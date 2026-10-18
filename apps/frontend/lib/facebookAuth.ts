/** Facebook OAuth 2.0 integration utilities. */

declare global {
  interface Window {
    FB?: {
      init: (params: FacebookInitParams) => void;
      login: (callback: (response: FacebookLoginResponse) => void, options?: FacebookLoginOptions) => void;
      logout: (callback: () => void) => void;
      getLoginStatus: (callback: (response: FacebookLoginStatusResponse) => void) => void;
      api: ((path: string, callback: (response: any) => void) => void) &
           ((path: string, params: any, callback: (response: any) => void) => void);
    };
    fbAsyncInit?: () => void;
  }
}

interface FacebookInitParams {
  appId: string;
  cookie?: boolean;
  xfbml?: boolean;
  version: string;
}

interface FacebookLoginOptions {
  scope?: string;
  return_scopes?: boolean;
  auth_type?: string;
}

interface FacebookAuthResponse {
  accessToken: string;
  expiresIn: number;
  signedRequest: string;
  userID: string;
}

interface FacebookLoginResponse {
  status: 'connected' | 'not_authorized' | 'unknown';
  authResponse: FacebookAuthResponse | null;
}

interface FacebookLoginStatusResponse {
  status: 'connected' | 'not_authorized' | 'unknown';
  authResponse: FacebookAuthResponse | null;
}

/**
 * Load Facebook SDK script
 */
export function loadFacebookSDK(appId: string, locale: string = 'en_US'): Promise<void> {
  return new Promise((resolve, reject) => {
    // Check if already loaded
    if (window.FB) {
      resolve();
      return;
    }

    // Check if script tag already exists
    const existingScript = document.getElementById('facebook-jssdk');
    if (existingScript) {
      existingScript.addEventListener('load', () => resolve());
      existingScript.addEventListener('error', () => reject(new Error('Failed to load Facebook SDK')));
      return;
    }

    // Setup async init callback
    window.fbAsyncInit = function() {
      if (!window.FB) {
        reject(new Error('Facebook SDK loaded but FB object not available'));
        return;
      }

      window.FB.init({
        appId: appId,
        cookie: true,
        xfbml: true,
        version: 'v18.0', // Use latest stable version
      });

      resolve();
    };

    // Load the SDK asynchronously
    const script = document.createElement('script');
    script.id = 'facebook-jssdk';
    script.src = `https://connect.facebook.net/${locale}/sdk.js`;
    script.async = true;
    script.defer = true;
    script.crossOrigin = 'anonymous';
    script.onerror = () => reject(new Error('Failed to load Facebook SDK'));
    
    const firstScript = document.getElementsByTagName('script')[0];
    if (firstScript && firstScript.parentNode) {
      firstScript.parentNode.insertBefore(script, firstScript);
    } else {
      document.head.appendChild(script);
    }
  });
}

/**
 * Login with Facebook and get access token
 */
export function loginWithFacebookSDK(): Promise<string> {
  return new Promise((resolve, reject) => {
    if (!window.FB) {
      reject(new Error('Facebook SDK not loaded'));
      return;
    }

    window.FB.login((response) => {
      if (response.status === 'connected' && response.authResponse) {
        resolve(response.authResponse.accessToken);
      } else if (response.status === 'not_authorized') {
        reject(new Error('Bạn cần cấp quyền cho ứng dụng để đăng nhập'));
      } else {
        reject(new Error('Đăng nhập Facebook bị hủy hoặc thất bại'));
      }
    }, {
      scope: 'public_profile,email',
      return_scopes: true,
    });
  });
}

/**
 * Check current Facebook login status
 */
export function checkFacebookLoginStatus(): Promise<FacebookLoginStatusResponse> {
  return new Promise((resolve, reject) => {
    if (!window.FB) {
      reject(new Error('Facebook SDK not loaded'));
      return;
    }

    window.FB.getLoginStatus((response) => {
      resolve(response);
    });
  });
}

/**
 * Logout from Facebook
 */
export function logoutFromFacebook(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (!window.FB) {
      reject(new Error('Facebook SDK not loaded'));
      return;
    }

    window.FB.logout(() => {
      resolve();
    });
  });
}

/**
 * Get Facebook user profile
 */
export function getFacebookUserProfile(): Promise<any> {
  return new Promise((resolve, reject) => {
    if (!window.FB) {
      reject(new Error('Facebook SDK not loaded'));
      return;
    }

    window.FB.api('/me', { fields: 'id,name,email,picture' }, (response) => {
      if (response && !response.error) {
        resolve(response);
      } else {
        reject(new Error(response?.error?.message || 'Failed to get user profile'));
      }
    });
  });
}

/**
 * Open Facebook login popup and handle full flow
 */
export async function openFacebookPopup(
  appId: string,
  onSuccess: (accessToken: string) => void,
  onError?: (error: Error) => void,
): Promise<void> {
  try {
    // Load SDK if not already loaded
    await loadFacebookSDK(appId);
    
    // Perform login
    const accessToken = await loginWithFacebookSDK();
    
    // Call success callback
    onSuccess(accessToken);
  } catch (error) {
    const err = error instanceof Error ? error : new Error('Facebook login failed');
    onError?.(err);
    throw err;
  }
}
