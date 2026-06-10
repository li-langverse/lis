/** Shared client for lip.lilangverse.xyz account UI */
(function () {
  const API = (window.LIP_API_BASE || "").replace(/\/$/, "") || "/v1";

  function sessionKey() {
    return "lip_session";
  }

  function getSession() {
    return localStorage.getItem(sessionKey());
  }

  function setSession(token) {
    if (token) localStorage.setItem(sessionKey(), token);
    else localStorage.removeItem(sessionKey());
  }

  async function api(method, path, body, token) {
    const headers = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const bearer = token || getSession();
    if (bearer) headers.Authorization = "Bearer " + bearer;
    const res = await fetch(API + path, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    const text = await res.text();
    let data = {};
    try {
      data = text ? JSON.parse(text) : {};
    } catch (_) {
      data = { error: "parse_error", message: text };
    }
    if (!res.ok) {
      const err = new Error(data.message || res.statusText);
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  function show(el, msg, kind) {
    if (!el) return;
    el.textContent = msg || "";
    el.className = "msg" + (kind ? " " + kind : "");
    el.hidden = !msg;
  }

  function fmtCode(code) {
    return code.replace(/(.{4})/g, "$1 ").trim();
  }

  window.LipAccount = {
    api,
    getSession,
    setSession,
    show,
    fmtCode,
    API,
  };
})();
