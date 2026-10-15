/*
 * Frontend configuration.
 *
 * API_BASE is where the Flask backend lives.
 *  - Leave it as "" when the Flask app serves this frontend (same origin).
 *  - Set it to the full backend URL when the frontend is hosted separately,
 *    e.g. "https://api.drfeyseldermatology.com"
 */
window.CLINIC_CONFIG = {
  API_BASE: "",
  REQUEST_TIMEOUT_MS: 15000
};
