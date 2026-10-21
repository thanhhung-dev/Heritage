/** Google OAuth 2.0 integration utilities. */

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: GoogleIdConfiguration) => void;
          prompt: (momentListener?: (notification: PromptMomentNotification) => void) => void;
          renderButton: (parent: HTMLElement, options: GsiButtonConfiguration) => void;
          disableAutoSelect: () => void;
          revoke: (hint: string, callback: (response: RevocationResponse) => void) => void;
        };
      };
    };
  }
}

interface GoogleIdConfiguration {
  client_id: string;
  callback: (response: GoogleCredentialResponse) => void;
  auto_select?: boolean;
  cancel_on_tap_outside?: boolean;
  context?: 'signin' | 'signup' | 'use';
}

interface GoogleCredentialResponse {
  credential: string;
  select_by: string;
}

interface PromptMomentNotification {
  isDisplayed: () => boolean;
  isNotDisplayed: () => boolean;
  getNotDisplayedReason: () => string;
  isSkippedMoment: () => boolean;
  getSkippedReason: () => string;
  isDismissedMoment: () => boolean;
  getDismissedReason: () => string;
  getMomentType: () => string;
}

interface GsiButtonConfiguration {
  type?: 'standard' | 'icon';
  theme?: 'outline' | 'filled_blue' | 'filled_black';
  size?: 'large' | 'medium' | 'small';
  text?: 'signin_with' | 'signup_with' | 'continue_with' | 'signin';
  shape?: 'rectangular' | 'pill' | 'circle' | 'square';
  logo_alignment?: 'left' | 'center';
  width?: string;
  locale?: string;
}

interface RevocationResponse {
  successful: boolean;
  error?: string;
}

/**
 * Load Google Identity Services script
 */
export function loadGoogleScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    // Check if already loaded
    if (window.google?.accounts?.id) {
      resolve();
      return;
    }

    // Check if script tag already exists
    const existingScript = document.querySelector('script[src="https://accounts.google.com/gsi/client"]');
    if (existingScript) {
      existingScript.addEventListener('load', () => resolve());
      existingScript.addEventListener('error', () => reject(new Error('Failed to load Google Identity Services')));
      return;
    }

    // Create and load script
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Failed to load Google Identity Services'));
    document.head.appendChild(script);
  });
}

/**
 * Initialize Google One Tap login
 */
export function initializeGoogleOneTap(
  clientId: string,
  onSuccess: (credential: string) => void,
  onError?: (error: Error) => void
): void {
  if (!window.google?.accounts?.id) {
    onError?.(new Error('Google Identity Services not loaded'));
    return;
  }

  window.google.accounts.id.initialize({
    client_id: clientId,
    callback: (response) => {
      if (response.credential) {
        onSuccess(response.credential);
      } else {
        onError?.(new Error('No credential received from Google'));
      }
    },
    auto_select: false,
    cancel_on_tap_outside: true,
  });
}

/**
 * Show Google One Tap prompt
 */
export function showGoogleOneTap(): void {
  if (window.google?.accounts?.id) {
    window.google.accounts.id.prompt();
  }
}

/**
 * Render Google Sign-In button
 */
export function renderGoogleButton(
  element: HTMLElement,
  clientId: string,
  onSuccess: (credential: string) => void,
  onError?: (error: Error) => void,
  options?: Partial<GsiButtonConfiguration>
): void {
  if (!window.google?.accounts?.id) {
    onError?.(new Error('Google Identity Services not loaded'));
    return;
  }

  // Initialize first
  initializeGoogleOneTap(clientId, onSuccess, onError);

  // Render button
  window.google.accounts.id.renderButton(element, {
    type: 'standard',
    theme: 'outline',
    size: 'large',
    text: 'continue_with',
    shape: 'rectangular',
    logo_alignment: 'left',
    width: '100%',
    ...options,
  });
}

/**
 * Open Google Sign-In popup (alternative to One Tap)
 */
export async function openGooglePopup(
  clientId: string,
  onSuccess: (credential: string) => void,
  onError?: (error: Error) => void
): Promise<void> {
  try {
    await loadGoogleScript();
    initializeGoogleOneTap(clientId, onSuccess, onError);
    showGoogleOneTap();
  } catch (error) {
    onError?.(error instanceof Error ? error : new Error('Failed to initialize Google login'));
  }
}

export interface GoogleIdTokenClaims {
  email?: string;
  name?: string;
  /** Google profile photo URL (`picture` claim). */
  picture?: string;
}

/**
 * Decode the profile claims from a Google ID token on the client.
 *
 * The backend has already verified the token signature; we only read the
 * public claims here because the auth API does not return the Google avatar.
 */
export function decodeGoogleIdToken(idToken: string): GoogleIdTokenClaims {
  try {
    const payload = idToken.split('.')[1];
    if (!payload) return {};

    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, '=');
    const binary = atob(padded);
    const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
    const claims = JSON.parse(new TextDecoder().decode(bytes)) as Record<string, unknown>;

    return {
      email: typeof claims.email === 'string' ? claims.email : undefined,
      name: typeof claims.name === 'string' ? claims.name : undefined,
      picture: typeof claims.picture === 'string' ? claims.picture : undefined,
    };
  } catch {
    return {};
  }
}
