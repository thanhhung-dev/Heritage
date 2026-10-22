/**
 * Icon lookup for the Profile feature's gamification UI.
 *
 * The backend badge/milestone catalogues (`GET /api/profile/badges`,
 * `GET /api/profile/milestones`) only send a string `icon_key` (e.g.
 * "BankOutlined") — this map resolves that key to the matching Ant Design
 * icon component for rendering. Keys here must stay in sync with the
 * `icon_key` values seeded in `init_db.py`.
 */

import {
  BankOutlined,
  BookOutlined,
  CalendarOutlined,
  CompassOutlined,
  BarsOutlined,
  EnvironmentOutlined,
  GlobalOutlined,
  RobotOutlined,
  SearchOutlined,
  SendOutlined,
  TrophyOutlined,
} from "@ant-design/icons";
import type { ReactNode } from "react";

const BADGE_ICON_MAP: Record<string, ReactNode> = {
  BankOutlined: <BankOutlined />,
  CompassOutlined: <CompassOutlined />,
  BookOutlined: <BookOutlined />,
  BarsOutlined: <BarsOutlined />,
  EnvironmentOutlined: <EnvironmentOutlined />,
  GlobalOutlined: <GlobalOutlined />,
  SearchOutlined: <SearchOutlined />,
  CalendarOutlined: <CalendarOutlined />,
  RobotOutlined: <RobotOutlined />,
  SendOutlined: <SendOutlined />,
};

/** Resolve a badge's `icon_key` to its icon component, with a safe fallback. */
export function getBadgeIcon(iconKey: string): ReactNode {
  return BADGE_ICON_MAP[iconKey] ?? <TrophyOutlined />;
}


