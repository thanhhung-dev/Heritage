export interface PublicAccount {
  displayName: string;
  email?: string;
  avatarUrl?: string;
}

export type AuthMode = "login" | "register";
