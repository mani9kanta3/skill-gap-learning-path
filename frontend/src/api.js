/*
  One axios instance for the whole app.

  There is no login, so no token interceptor. The timeout is generous
  because the path preview replays the planning rules on the whole
  dataset the first time it runs.
*/

import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 30000,
});

/*
  Refuse a reply that is not JSON.

  If VITE_API_URL is not set, axios asks the site itself, the dev server
  answers with index.html and a 200, and the page goes blank trying to
  read fields off a string. A 200 carrying HTML is not a successful API
  call, so it becomes one clear sentence instead.
*/
api.interceptors.response.use((response) => {
  const looksLikeHtml =
    typeof response.data === "string" && response.data.trim().startsWith("<");

  if (looksLikeHtml) {
    return Promise.reject(
      new Error(
        "The API address is not set correctly, so the site asked itself " +
          "instead of the server. Check VITE_API_URL."
      )
    );
  }

  return response;
});

export default api;
