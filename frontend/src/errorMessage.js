/*
  FastAPI sends errors back in a few shapes. This turns any of them into
  one plain sentence a page can show.
*/

function getErrorMessage(error, fallback = "Something went wrong. Please try again.") {
  if (error && error.code === "ECONNABORTED") {
    return "The server took too long to answer. Please try again.";
  }

  // Thrown by the interceptor in api.js, or the server is not running.
  if (error && error.message && !error.response) {
    if (error.message === "Network Error") {
      return "Could not reach the API. Is the backend running on the address in VITE_API_URL?";
    }
    return error.message;
  }

  const data = error && error.response && error.response.data;

  if (!data) {
    return fallback;
  }

  // {"detail": "No employee with that id."}
  if (typeof data.detail === "string") {
    return data.detail;
  }

  /*
    A 422 from Pydantic: {"detail": [{"loc": ["body", "planning_date"], "msg": "..."}]}
    The last part of loc is the field name, the only bit a person needs.
  */
  if (Array.isArray(data.detail)) {
    const messages = data.detail.map((item) => {
      const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : "";
      const message = String(item.msg || "").replace(/^Value error, /, "");
      return field && field !== "body" ? `${field}: ${message}` : message;
    });
    return messages.join(" ");
  }

  return fallback;
}

export default getErrorMessage;
