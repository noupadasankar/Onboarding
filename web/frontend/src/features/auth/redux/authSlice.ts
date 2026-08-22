import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { AuthResponse } from '@hr-onboarding/shared';
import { AUTH_STORAGE_KEY } from '../constants';
import type { AuthState } from '../types';

/** Rehydrate the session from localStorage so a refresh keeps the user logged in. */
function loadInitialState(): AuthState {
  const empty: AuthState = { user: null, accessToken: null, refreshToken: null };
  if (typeof localStorage === 'undefined') return empty;
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as AuthState) : empty;
  } catch {
    return empty;
  }
}

function persist(state: AuthState): void {
  if (typeof localStorage === 'undefined') return;
  if (state.accessToken) localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(state));
  else localStorage.removeItem(AUTH_STORAGE_KEY);
}

const authSlice = createSlice({
  name: 'auth',
  initialState: loadInitialState(),
  reducers: {
    setCredentials(state, action: PayloadAction<AuthResponse>) {
      state.user = action.payload.user;
      state.accessToken = action.payload.tokens.accessToken;
      state.refreshToken = action.payload.tokens.refreshToken;
      persist(state);
    },
    clearCredentials(state) {
      state.user = null;
      state.accessToken = null;
      state.refreshToken = null;
      persist(state);
    },
  },
});

export const { setCredentials, clearCredentials } = authSlice.actions;
export default authSlice.reducer;
