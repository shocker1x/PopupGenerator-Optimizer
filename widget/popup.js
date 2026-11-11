(() => {
  const script = document.currentScript;
  if (!script) return;

  const campaignId = script.dataset.campaignId;
  if (!campaignId) return;

  const apiBase = new URL(script.src, document.baseURI).origin;
  const frequencyDays = 7;
  const storageFallback = new Map();
  const keys = {
    visitor: 'fieldnote:visitor',
    shown: `fieldnote:${campaignId}:shown-until`,
    subscribed: `fieldnote:${campaignId}:subscribed`,
  };

  function readStorage(key) {
    try {
      return window.localStorage.getItem(key);
    } catch {
      return storageFallback.get(key) || null;
    }
  }

  function writeStorage(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch {
      storageFallback.set(key, value);
    }
  }

  function makeId() {
    if (window.crypto && typeof window.crypto.randomUUID === 'function') {
      return window.crypto.randomUUID();
    }
    const bytes = new Uint8Array(16);
    window.crypto.getRandomValues(bytes);
    return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
  }

  function getVisitorId() {
    let visitorId = readStorage(keys.visitor);
    if (!visitorId) {
      visitorId = makeId();
      writeStorage(keys.visitor, visitorId);
    }
    return visitorId;
  }

  function isSuppressed() {
    if (readStorage(keys.subscribed) === 'true') return true;
    const shownUntil = Number(readStorage(keys.shown) || 0);
    return shownUntil > Date.now();
  }

  const css = `
    :host { all: initial; display: block; color-scheme: light; }
    *, *::before, *::after { box-sizing: border-box; }
    .backdrop { position: fixed; inset: 0; z-index: 2147483000; display: grid; place-items: center; padding: 20px; background: rgba(15, 25, 20, .52); font-family: var(--popup-font, Arial, sans-serif); }
    .dialog { position: relative; display: grid; grid-template-columns: minmax(0, 1fr); width: min(100%, 440px); max-height: min(90vh, 700px); overflow: auto; padding: 36px; border-radius: var(--popup-radius, 10px); color: var(--popup-ink, #20332c); background: var(--popup-bg, #fff); box-shadow: 0 24px 80px rgba(0, 0, 0, .28); animation: appear .24s ease-out both; }
    .dialog.layout-split { grid-template-columns: minmax(110px, .75fr) minmax(0, 1.25fr); gap: 20px; align-items: center; }
    .dialog.layout-compact { width: min(100%, 340px); padding: 25px; }
    .dismiss { position: absolute; top: 12px; right: 12px; display: grid; place-items: center; width: 32px; height: 32px; padding: 0; border: 1px solid color-mix(in srgb, var(--popup-ink), transparent 82%); border-radius: 50%; color: var(--popup-ink); background: transparent; font: 20px/1 Arial, sans-serif; cursor: pointer; }
    .artwork { width: 100%; max-height: 220px; margin: 0 0 18px; border-radius: max(0px, calc(var(--popup-radius, 10px) - 4px)); object-fit: cover; }
    .layout-split .artwork { height: 220px; margin: 0; }
    .layout-compact .artwork { max-height: 130px; }
    .offer { display: inline-block; max-width: 100%; padding: 6px 9px; margin: 0 35px 11px 0; border-radius: 3px; color: var(--popup-bg); background: var(--popup-accent); font: 700 11px/1.35 Arial, sans-serif; }
    h2 { margin: 0 32px 10px 0; color: var(--popup-ink); font: 700 29px/1.12 var(--popup-font, Arial, sans-serif); }
    .description { margin: 0 0 20px; color: color-mix(in srgb, var(--popup-ink), transparent 22%); font: 400 14px/1.55 var(--popup-font, Arial, sans-serif); }
    form { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 8px; }
    input { min-width: 0; height: 45px; padding: 0 12px; border: 1px solid color-mix(in srgb, var(--popup-ink), transparent 78%); border-radius: max(2px, calc(var(--popup-radius, 10px) - 4px)); outline: none; color: var(--popup-ink); background: transparent; font: 400 13px Arial, sans-serif; }
    input:focus { border-color: var(--popup-accent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--popup-accent), transparent 82%); }
    .submit { min-height: 45px; padding: 0 15px; border: 0; border-radius: max(2px, calc(var(--popup-radius, 10px) - 4px)); color: var(--popup-bg); background: var(--popup-accent); font: 700 12px Arial, sans-serif; cursor: pointer; }
    .submit:disabled { cursor: wait; opacity: .7; }
    .consent { display: flex; gap: 5px; align-items: flex-start; margin: 12px 0 0; color: color-mix(in srgb, var(--popup-ink), transparent 43%); font: 400 10px/1.45 Arial, sans-serif; }
    .consent-mark { flex: 0 0 auto; font-weight: 700; }
    .status { min-height: 16px; margin: 8px 0 0; color: var(--popup-ink); font: 400 11px/1.45 Arial, sans-serif; }
    .status.error { color: #a33b2d; }
    @keyframes appear { from { opacity: 0; transform: translateY(8px) scale(.99); } to { opacity: 1; transform: translateY(0) scale(1); } }
    @media (max-width: 520px) { .dialog, .dialog.layout-split { display: block; width: min(100%, 390px); padding: 27px 22px 22px; } .dialog.layout-split .artwork { height: 130px; margin-bottom: 16px; } h2 { font-size: 24px; } form { grid-template-columns: 1fr; } .submit { width: 100%; } }
    @media (prefers-reduced-motion: reduce) { .dialog { animation: none; } }
  `;

  function createElement(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function renderPopup(campaign, version, config) {
    const host = document.createElement('div');
    host.setAttribute('data-fieldnote-widget', campaign);
    const shadow = host.attachShadow({ mode: 'closed' });
    const style = document.createElement('style');
    style.textContent = css;

    const backdrop = createElement('div', 'backdrop');
    const dialog = createElement('section', `dialog layout-${config.layout}`);
    dialog.setAttribute('role', 'dialog');
    dialog.setAttribute('aria-modal', 'true');
    dialog.setAttribute('aria-labelledby', 'fieldnote-popup-title');
    dialog.setAttribute('aria-describedby', 'fieldnote-popup-description');
    dialog.style.setProperty('--popup-bg', config.theme.background_color);
    dialog.style.setProperty('--popup-ink', config.theme.text_color);
    dialog.style.setProperty('--popup-accent', config.theme.accent_color);
    dialog.style.setProperty('--popup-radius', `${config.theme.border_radius}px`);

    const fontFamilies = {
      system: 'Arial, sans-serif',
      inter: 'Inter, Arial, sans-serif',
      roboto: 'Roboto, Arial, sans-serif',
      georgia: 'Georgia, serif',
      montserrat: 'Montserrat, Arial, sans-serif',
      lato: 'Lato, Arial, sans-serif',
    };
    dialog.style.setProperty('--popup-font', fontFamilies[config.theme.font] || fontFamilies.system);

    const closeButton = createElement('button', 'dismiss', '×');
    closeButton.type = 'button';
    closeButton.setAttribute('aria-label', 'Close signup popup');
    const content = createElement('div', 'content');
    const title = createElement('h2', '', config.headline);
    title.id = 'fieldnote-popup-title';
    const description = createElement('p', 'description', config.description);
    description.id = 'fieldnote-popup-description';

    let artwork = null;
    if (config.image) {
      artwork = document.createElement('img');
      artwork.className = 'artwork';
      artwork.src = config.image;
      artwork.alt = 'Popup artwork';
      artwork.loading = 'lazy';
    }

    if (config.offer && !config.offer.requires_owner_approval) {
      content.append(createElement('p', 'offer', config.offer.text));
    }
    content.append(title, description);

    const form = document.createElement('form');
    const email = document.createElement('input');
    email.type = 'email';
    email.name = 'email';
    email.required = true;
    email.autocomplete = 'email';
    email.placeholder = config.email_placeholder;
    email.setAttribute('aria-label', config.email_placeholder);
    const submit = createElement('button', 'submit', config.cta);
    submit.type = 'submit';
    form.append(email, submit);

    const consent = createElement('p', 'consent');
    consent.append(createElement('span', 'consent-mark', '✓'));
    consent.append(document.createTextNode(config.consent_text));
    const status = createElement('p', 'status');
    status.setAttribute('aria-live', 'polite');
    content.append(form, consent, status);
    dialog.append(closeButton, content);
    if (artwork) {
      if (config.layout === 'split') dialog.insertBefore(artwork, content);
      else content.prepend(artwork);
    }
    backdrop.append(dialog);
    shadow.append(style, backdrop);
    document.body.append(host);

    const previousFocus = document.activeElement;
    let closed = false;
    const close = () => {
      if (closed) return;
      closed = true;
      host.remove();
      if (previousFocus && typeof previousFocus.focus === 'function') previousFocus.focus();
    };
    const focusable = () => Array.from(dialog.querySelectorAll('button:not(:disabled), input:not(:disabled)'));
    closeButton.addEventListener('click', close);
    backdrop.addEventListener('click', (event) => {
      if (event.target === backdrop) close();
    });
    shadow.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        close();
        return;
      }
      if (event.key !== 'Tab') return;
      const items = focusable();
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && shadow.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && shadow.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    });

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (!email.reportValidity()) return;
      submit.disabled = true;
      status.className = 'status';
      status.textContent = 'Submitting…';
      try {
        const response = await fetch(`${apiBase}/api/public/subscribe`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            campaign_id: campaign,
            version_id: version,
            visitor_id: getVisitorId(),
            email: email.value.trim(),
            consent_text: config.consent_text,
          }),
        });
        if (!response.ok) throw new Error('Signup service is not available yet. Please try again later.');
        writeStorage(keys.subscribed, 'true');
        status.textContent = 'You’re on the list. Thanks for being here.';
        form.remove();
      } catch (error) {
        status.className = 'status error';
        status.textContent = error.message || 'Could not submit right now. Please try again.';
        submit.disabled = false;
      }
    });

    window.requestAnimationFrame(() => email.focus());
    return close;
  }

  async function start() {
    if (isSuppressed()) return;
    let published;
    try {
      const response = await fetch(`${apiBase}/api/public/campaigns/${encodeURIComponent(campaignId)}/config`, {
        headers: { Accept: 'application/json' },
      });
      if (!response.ok) return;
      published = await response.json();
    } catch {
      return;
    }

    const config = published.config;
    let shown = false;
    let timerId = 0;
    let removeTriggerListeners = () => {};
    const show = () => {
      if (shown || isSuppressed()) return;
      shown = true;
      window.clearTimeout(timerId);
      removeTriggerListeners();
      writeStorage(keys.shown, String(Date.now() + frequencyDays * 24 * 60 * 60 * 1000));
      renderPopup(published.campaign_id, published.version_id, config);
    };

    if (config.trigger.type === 'time_delay') {
      timerId = window.setTimeout(show, config.trigger.delay_seconds * 1000);
      return;
    }

    if (config.trigger.type === 'scroll_percentage') {
      const onScroll = () => {
        const scrollable = document.documentElement.scrollHeight - window.innerHeight;
        if (scrollable <= 0) return;
        const percent = (window.scrollY / scrollable) * 100;
        if (percent >= config.trigger.scroll_percentage) show();
      };
      window.addEventListener('scroll', onScroll, { passive: true });
      removeTriggerListeners = () => window.removeEventListener('scroll', onScroll);
      return;
    }

    const mobile = window.matchMedia('(pointer: coarse)').matches || window.innerWidth < 700;
    if (!mobile) {
      const onExit = (event) => {
        if (event.clientY <= 0 && event.relatedTarget == null) show();
      };
      document.addEventListener('mouseout', onExit);
      removeTriggerListeners = () => document.removeEventListener('mouseout', onExit);
      return;
    }

    let previousScrollY = window.scrollY;
    const onMobileScroll = () => {
      const currentScrollY = window.scrollY;
      if (currentScrollY < previousScrollY && previousScrollY > 120) show();
      previousScrollY = currentScrollY;
    };
    window.addEventListener('scroll', onMobileScroll, { passive: true });
    removeTriggerListeners = () => window.removeEventListener('scroll', onMobileScroll);
    timerId = window.setTimeout(show, 15_000);
  }

  void start();
})();