/** Shared types for the Profile feature UI. */

export interface SocialLinks {
  instagram?: string;
  linkedin?: string;
  twitter?: string;
}

export interface ProfileData {
  display_name: string;
  handle: string;
  avatar_url?: string;
  banner_url?: string;
  bio?: string;
  country?: string;
  city?: string;
  display_email: boolean;
  joined_at?: string;
  socials?: SocialLinks;
  total_hours?: number;
  level?: string;
  featured_badges?: string[];
  show_activity_on_profile?: boolean;
}

export interface PersonalizationConsent {
  analytics_opt_in: boolean;
}

export type ProfileTabKey = "personal" | "milestones" | "achievements";
export type ExploreSubTabKey = "recent" | "journeys";

/**
 * A single collectible gamification badge, as returned by the backend
 * (`GET /api/profile/badges`, Pydantic `BadgeResponse`). Field names mirror
 * the API response exactly so no mapping layer is needed on the wire.
 */
export interface Badge {
  id: string;
  title: string;
  description: string;
  icon_key: string;
  is_unlocked: boolean;
  earned_at?: string | null;
}

/** A single checklist task inside a milestone level (`MilestoneTaskResponse`). */
export interface MilestoneTask {
  id: string;
  title: string;
  is_completed: boolean;
}

/** A gamification level grouping a set of milestone tasks (`MilestoneLevelResponse`). */
export interface MilestoneLevel {
  id: string;
  level_name: string;
  description: string;
  is_unlocked: boolean;
  tasks: MilestoneTask[];
}

