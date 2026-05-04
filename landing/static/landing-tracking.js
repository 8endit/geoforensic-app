// Shared lead-funnel tracking helper for bodenbericht.de
// - Captures UTM params from location.search once on load
// - Exposes window.bbBuildPayload(base) to merge UTMs into any /api/leads body
// - Exposes window.bbTrack(event, extra) to push consistent events to dataLayer
//
// Loaded as a regular <script> on every page that has a lead form. Klaro
// gates GTM, so dataLayer pushes that happen before consent are simply
// queued — Klaro replays them when GTM activates.

(function () {
  var STORAGE_KEY = 'bb_utm_v1';
  var UTM_KEYS = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'gclid', 'fbclid'];

  function parseUtm() {
    try {
      var qs = new URLSearchParams(window.location.search || '');
      var found = {};
      var any = false;
      UTM_KEYS.forEach(function (k) {
        var v = qs.get(k);
        if (v) { found[k] = v; any = true; }
      });
      return any ? found : null;
    } catch (e) {
      return null;
    }
  }

  function loadStoredUtm() {
    try {
      var raw = sessionStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      var parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== 'object') return null;
      // expire after 90 minutes
      if (parsed._t && (Date.now() - parsed._t) > 90 * 60 * 1000) return null;
      return parsed;
    } catch (e) {
      return null;
    }
  }

  function persistUtm(utm) {
    try {
      var withTs = Object.assign({}, utm, { _t: Date.now() });
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(withTs));
    } catch (e) { /* ignore */ }
  }

  // Resolve UTMs: URL > sessionStorage > none.
  var fresh = parseUtm();
  if (fresh) persistUtm(fresh);
  var stored = loadStoredUtm();
  // Strip the timestamp before exposing
  if (stored && stored._t) { delete stored._t; }
  window.__bbUtm = fresh || stored || null;

  /**
   * Merge stored UTMs into a payload's `answers` field. Returns a NEW object;
   * does not mutate. Safe to call with no UTMs (returns base unchanged).
   */
  window.bbBuildPayload = function (base) {
    base = base || {};
    if (!window.__bbUtm) return base;
    var answers = Object.assign({}, base.answers || {});
    Object.keys(window.__bbUtm).forEach(function (k) {
      // Don't overwrite if caller already set this key
      if (answers[k] === undefined) answers[k] = window.__bbUtm[k];
    });
    return Object.assign({}, base, { answers: answers });
  };

  /**
   * Push a consistent event to dataLayer. Event names are snake_case.
   * Always includes referrer + page path for context.
   */
  window.bbTrack = function (event, extra) {
    try {
      window.dataLayer = window.dataLayer || [];
      var payload = Object.assign(
        {
          event: event,
          page_path: window.location.pathname,
          page_referrer: document.referrer || '',
        },
        window.__bbUtm || {},
        extra || {}
      );
      window.dataLayer.push(payload);
    } catch (e) { /* ignore */ }
  };

  /**
   * Convenience: emit lead_submitted / lead_failed pair around a fetch.
   * Pass the source string and the fetch Response (or {ok:false, status:0} on network error).
   */
  window.bbTrackLeadResult = function (source, res, extra) {
    if (res && res.ok) {
      window.bbTrack('lead_submitted', Object.assign({ source: source, status: res.status }, extra || {}));
    } else {
      window.bbTrack('lead_failed', Object.assign({ source: source, status: (res && res.status) || 0 }, extra || {}));
    }
  };

  /**
   * Shared lead-submit helper. Replaces ~7 near-duplicate handlers across
   * index.html / quiz.html / persona pages.
   *
   * opts: {
   *   source: string,                  // lead source, e.g. 'hero_direct'
   *   payload: object,                  // POST body (without UTMs; bbBuildPayload merges them)
   *   formId: string,                   // id of <form>, hidden on success
   *   successId: string,                // id of element to show on success
   *   errorId?: string,                 // id of inline error box (preferred); if absent, fallback noop
   *   errorMsgId?: string,              // id of <p> inside errorId for the message text
   *   btn: HTMLButtonElement,           // submit button to disable
   *   busyLabel?: string,               // optional label override during fetch
   *   resetLabel?: string,              // optional label to restore on error
   *   resetLabelEl?: HTMLElement,       // element whose textContent holds the label (defaults to btn)
   * }
   *
   * Returns the Response (or null on network error).
   */
  window.bbSubmitLead = async function (opts) {
    var source = opts.source;
    var btn = opts.btn;
    var resetEl = opts.resetLabelEl || btn;
    var originalLabel = resetEl ? resetEl.textContent : null;

    if (btn) btn.disabled = true;
    if (opts.busyLabel && resetEl) resetEl.textContent = opts.busyLabel;

    function showError(message) {
      if (opts.errorId) {
        var box = document.getElementById(opts.errorId);
        if (box) {
          if (opts.errorMsgId) {
            var msgEl = document.getElementById(opts.errorMsgId);
            if (msgEl) msgEl.textContent = message;
          }
          box.classList.remove('hidden');
          // a11y: role=alert/aria-live should already be on the box; reset focus
          try { box.setAttribute('tabindex', '-1'); box.focus({ preventScroll: false }); } catch (e) {}
        }
      }
    }

    try {
      var payload = (window.bbBuildPayload || function (b) { return b; })(opts.payload || {});
      // Read honeypot field if a form is referenced. Browsers fill it via
      // autofill quirks too, so we only forward when actually non-empty.
      try {
        var formEl = opts.formId ? document.getElementById(opts.formId) : null;
        var hp = formEl ? formEl.querySelector('input[name="website"]') : null;
        var hpVal = hp ? String(hp.value || '').trim() : '';
        if (hpVal) payload.website = hpVal;
      } catch (e) { /* noop */ }
      var res = await fetch('/api/leads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      window.bbTrackLeadResult(source, res);
      if (!res.ok) {
        var data = await res.json().catch(function () { return {}; });
        var msg = (data && data.detail) || 'Senden fehlgeschlagen. Bitte prüfen Sie die Adresse und versuchen Sie es erneut.';
        showError(msg);
        if (btn) btn.disabled = false;
        if (resetEl && opts.resetLabel) resetEl.textContent = opts.resetLabel;
        else if (resetEl && originalLabel != null) resetEl.textContent = originalLabel;
        return res;
      }
      // Success: hide form, show success element
      if (opts.formId) {
        var form = document.getElementById(opts.formId);
        if (form) form.classList.add('hidden');
      }
      if (opts.successId) {
        var ok = document.getElementById(opts.successId);
        if (ok) ok.classList.remove('hidden');
      }
      return res;
    } catch (err) {
      window.bbTrackLeadResult(source, null, { error_message: String((err && err.message) || err) });
      showError('Verbindung fehlgeschlagen. Bitte prüfen Sie Ihre Internetverbindung und versuchen Sie es erneut.');
      if (btn) btn.disabled = false;
      if (resetEl && opts.resetLabel) resetEl.textContent = opts.resetLabel;
      else if (resetEl && originalLabel != null) resetEl.textContent = originalLabel;
      return null;
    }
  };
})();

// Klaro consent change: emit dataLayer events so GTM can react and so we
// can measure the consent rate per session. Re-fires on every change.
(function () {
  function emit(name) {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({ event: name });
  }
  function attach() {
    if (!window.klaro || !window.klaro.getManager) return false;
    try {
      var mgr = window.klaro.getManager();
      if (!mgr || typeof mgr.watch !== 'function') return false;
      mgr.watch({
        update: function (_obj, type, data) {
          if (type === 'consents' && data) {
            // Aggregate across services: any analytics accepted -> consent_granted
            var analyticsAccepted = !!(data['google-analytics-4'] || data['posthog']);
            emit(analyticsAccepted ? 'consent_granted' : 'consent_declined');

            // Auto-enable the GTM orchestrator service iff at least one of
            // GA4/PostHog was accepted. This keeps the per-tool toggle in
            // the consent modal granular while ensuring GTM (the loader)
            // actually fires when needed.
            try {
              var current = !!data['google-tag-manager'];
              if (analyticsAccepted && !current) {
                mgr.updateConsent('google-tag-manager', true);
                mgr.saveAndApplyConsents();
              } else if (!analyticsAccepted && current) {
                mgr.updateConsent('google-tag-manager', false);
                mgr.saveAndApplyConsents();
              }
            } catch (e) { /* non-fatal */ }
          }
        }
      });
      return true;
    } catch (e) { return false; }
  }
  // Klaro loads with `defer`; poll briefly until manager exists.
  var tries = 0;
  var iv = setInterval(function () {
    if (attach() || ++tries > 25) clearInterval(iv);
  }, 200);
})();
