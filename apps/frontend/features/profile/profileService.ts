/** Profile service for API calls. */

import { API_BASE_URL } from "@/config/api";
import { getAuthHeader } from "@/lib/auth";
import type { Badge, MilestoneLevel, PersonalizationConsent, ProfileData } from "./types";

export interface ErrorResponse {
  detail: string;
}

/**
 * Fetch the signed-in user's profile.
 */
export async function getProfile(): Promise<ProfileData> {
  const response = await fetch(`${API_BASE_URL}/profile/me`, {
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
  });

  const json = await response.json();

  if (!response.ok) {
    const error = json as ErrorResponse;
    throw new Error(error.detail || "Could not load profile.");
  }

  return json as ProfileData;
}

/**
 * Persist profile edits made from the Edit profile form.
 */
export async function updateProfile(data: Partial<ProfileData>): Promise<ProfileData> {
  const response = await fetch(`${API_BASE_URL}/profile/me`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
    body: JSON.stringify(data),
  });

  const json = await response.json();

  if (!response.ok) {
    const error = json as ErrorResponse;
    throw new Error(error.detail || "Could not save profile.");
  }

  return json as ProfileData;
}

/**
 * Fetch the signed-in user's personalization consent.
 */
export async function getPersonalizationConsent(): Promise<PersonalizationConsent> {
  const response = await fetch(`${API_BASE_URL}/profile/consent`, {
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
  });

  const json = await response.json();

  if (!response.ok) {
    const error = json as ErrorResponse;
    throw new Error(error.detail || "Could not load personalization consent.");
  }

  return json as PersonalizationConsent;
}

/**
 * Persist the signed-in user's personalization consent.
 */
export async function updatePersonalizationConsent(
  analyticsOptIn: boolean,
): Promise<PersonalizationConsent> {
  const response = await fetch(`${API_BASE_URL}/profile/consent`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
    body: JSON.stringify({ analytics_opt_in: analyticsOptIn }),
  });

  const json = await response.json();

  if (!response.ok) {
    const error = json as ErrorResponse;
    throw new Error(error.detail || "Could not update personalization consent.");
  }

  return json as PersonalizationConsent;
}

/**
 * Fetch the gamification badge catalogue, merged with the signed-in user's
 * unlock state (`GET /api/profile/badges`).
 */
export async function getBadges(): Promise<Badge[]> {
  const response = await fetch(`${API_BASE_URL}/profile/badges`, {
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
  });

  const json = await response.json();

  if (!response.ok) {
    const error = json as ErrorResponse;
    throw new Error(error.detail || "Could not load badges.");
  }

  return json as Badge[];
}

/**
 * Fetch the gamification milestone levels, merged with the signed-in user's
 * task completion state (`GET /api/profile/milestones`).
 */
export async function getMilestones(): Promise<MilestoneLevel[]> {
  const response = await fetch(`${API_BASE_URL}/profile/milestones`, {
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
  });

  const json = await response.json();

  if (!response.ok) {
    const error = json as ErrorResponse;
    throw new Error(error.detail || "Could not load milestones.");
  }

  return json as MilestoneLevel[];
}

