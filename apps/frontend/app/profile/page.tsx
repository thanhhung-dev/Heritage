import type { Metadata } from "next";
import { ProfilePage } from "@/features/profile/ProfilePage";

export const metadata: Metadata = {
  title: "Hồ sơ cá nhân",
  description: "Quản lý hồ sơ, cột mốc khám phá và huy hiệu di sản của bạn.",
};

export default function Page() {
  return <ProfilePage />;
}
