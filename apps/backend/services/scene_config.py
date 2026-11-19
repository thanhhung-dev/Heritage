"""Store scene configuration in existing viewer columns, preserving asset ownership."""
import math

from fastapi import HTTPException
from sqlalchemy import select

from apps.backend.core.assets import asset_policy
from apps.backend.models.model_asset import ModelAsset
from apps.backend.models.scene import Scene
from apps.backend.models.sky_preset import SkyPreset
from apps.backend.schemas.heritage import ModelAssetOut, SkyPresetOut
from apps.backend.schemas.scene_config import SceneConfigOut, SceneConfigUpdate, safe_asset_reference
from apps.backend.services.admin_scene import SceneService

CAMERA_COLUMNS = {
    "node_name": "camera_node_name", "start_position": "cam_start_pos", "start_target": "cam_start_target",
    "zoom_position": "cam_zoom_pos", "zoom_target": "cam_zoom_target",
    "path_url": "camera_path_url", "instant_move": "instant_move",
}


class SceneConfigService(SceneService):
    async def locate(self, scene_id, *, lock=False):
        heritage_id = await self.db.scalar(select(Scene.heritage_id).where(Scene.id == scene_id))
        if heritage_id is None:
            raise HTTPException(404, "Scene not found.")
        await self.heritage(heritage_id, lock=lock)
        return await self.scene(heritage_id, scene_id)

    async def assets(self, scene_id):
        return list((await self.db.scalars(select(ModelAsset).where(
            ModelAsset.scene_id == scene_id).order_by(ModelAsset.lod_level, ModelAsset.id))).all())

    async def output(self, scene):
        policy = asset_policy()
        sky = await self.db.get(SkyPreset, scene.sky_preset_id) if scene.sky_preset_id is not None else None
        models = []
        for asset in await self.assets(scene.id):
            dto = ModelAssetOut.model_validate(asset)
            resolved = policy.resolve(asset.file_url)
            if resolved is None:
                raise HTTPException(422, "Scene model asset host is not allowed.")
            dto.file_url = resolved
            models.append(dto)
        camera = {field: getattr(scene, column) for field, column in CAMERA_COLUMNS.items()}
        camera["path_url"] = policy.resolve(camera["path_url"])
        return SceneConfigOut(scene_id=scene.id, heritage_id=scene.heritage_id, camera=camera,
                              sky_preset_id=scene.sky_preset_id,
                              sky=SkyPresetOut.model_validate(sky) if sky else None, models=models)

    async def get(self, scene_id):
        return await self.output(await self.locate(scene_id))

    async def save(self, scene_id, data: SceneConfigUpdate):
        scene = await self.locate(scene_id, lock=True)
        assets = await self.assets(scene_id)
        if data.model_asset_ids is not None and not set(data.model_asset_ids).issubset({asset.id for asset in assets}):
            raise HTTPException(422, "Every referenced model asset must exist and belong to this scene.")
        for asset in assets:
            try:
                safe_asset_reference(asset.file_url)
            except ValueError:
                raise HTTPException(422, "Scene contains an unsafe model asset reference.") from None
            if asset.format not in {"glb", "splat", "sog"} or asset.lod_level < 0:
                raise HTTPException(422, "Scene contains an invalid model asset format or LOD.")
        camera = data.camera.model_dump()
        if camera["path_url"] is not None:
            match = next((asset for asset in assets if asset.format == "glb" and (
                camera["path_url"] == asset.file_url or camera["path_url"] == asset_policy().resolve(asset.file_url))), None)
            if match is None:
                raise HTTPException(422, "Camera path must reference a registered GLB asset of this scene.")
            camera["path_url"] = match.file_url
        if data.sky_preset_id is not None:
            sky = await self.db.get(SkyPreset, data.sky_preset_id)
            if sky is None:
                raise HTTPException(422, "Sky preset does not exist.")
            # Presets are shared records: select and validate, never mutate them.
            bounds = {"turbidity": (0, 100), "rayleigh": (0, 100), "mie_coefficient": (0, 1),
                      "mie_directional_g": (-1, 1), "elevation": (-90, 90), "azimuth": (-360, 360),
                      "exposure": (0, 100), "cloud_coverage": (0, 1), "cloud_density": (0, 1), "stars": (0, 1)}
            for field, (lower, upper) in bounds.items():
                value = getattr(sky, field)
                if value is not None and (not math.isfinite(value) or not lower <= value <= upper):
                    raise HTTPException(422, f"Sky preset {field} must be finite and within [{lower}, {upper}].")
        for field, column in CAMERA_COLUMNS.items():
            setattr(scene, column, camera[field])
        scene.sky_preset_id = data.sky_preset_id
        # Build the DTO before commit, so a disallowed asset host cannot leave
        # a successful write behind an error response.
        result = await self.output(scene)
        await self.commit()
        return result
