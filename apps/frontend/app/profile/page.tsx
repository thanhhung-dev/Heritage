import type { Metadata } from "next";
import { ProfilePage } from "@/features/profile/ProfilePage";

export const metadata: Metadata = {
  title: "Profile | Heritage",
  description:
    "Manage your Heritage profile, personal information, milestones, and achievements.",
};

export default function ProfileRoute() {
  return <ProfilePage />;
}
