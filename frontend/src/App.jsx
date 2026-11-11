import { useState } from 'react';
import {
  ArrowDownRight,
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronDown,
  CircleHelp,
  Clock3,
  ExternalLink,
  Globe2,
  LayoutDashboard,
  LogOut,
  Mail,
  MousePointer2,
  Plus,
  ScanSearch,
  Sparkles,
  WandSparkles,
} from 'lucide-react';
import PopupPreview from './components/PopupPreview.jsx';
import {
  analyzeWebsite,
  authenticate,
  clearToken,
  generatePopups,
  getToken,
  setToken,
} from './services/api.js';

const toneNames = {
  friendly: 'Warm welcome',
  minimal: 'Quiet confidence',
  bold: 'Big energy',
};

function AuthScreen({ onAuthenticated }) {
  const [creating, setCreating] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      const result = await authenticate(email, password, creating);
      setToken(result.access_token);
      onAuthenticated(result.access_token, email);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-story">
        <div className="brand-lockup brand-lockup--light">
          <span className="brand-mark"><span /></span>
          <span>fieldnote</span>
        </div>
        <div className="auth-story-copy">
          <p className="eyebrow eyebrow--light">A better first hello</p>
          <h1>Make your first<br />visit feel personal.</h1>
          <p className="auth-story-text">Turn what makes your shop yours into a signup moment people actually welcome.</p>
        </div>
        <div className="auth-story-foot">
          <div className="story-spark"><Sparkles size={16} /></div>
          <span>Made for thoughtful independent brands</span>
          <span className="story-index">01 / 03</span>
        </div>
        <div className="auth-stamp" aria-hidden="true">A LITTLE<br />MORE HUMAN</div>
      </section>

      <section className="auth-panel">
        <div className="auth-mobile-brand brand-lockup">
          <span className="brand-mark"><span /></span>
          <span>fieldnote</span>
        </div>
        <div className="auth-form-wrap">
          <div className="auth-topline"><span>POPUP STUDIO</span><CircleHelp size={17} /></div>
          <p className="eyebrow">{creating ? 'YOUR STUDIO STARTS HERE' : 'GOOD TO SEE YOU'}</p>
          <h2>{creating ? 'Create your account' : 'Welcome back'}</h2>
          <p className="auth-intro">{creating ? 'A few details and you’re ready to build.' : 'Sign in to pick up where you left off.'}</p>

          <form className="auth-form" onSubmit={submit}>
            <label htmlFor="email">Work email</label>
            <div className="input-with-icon">
              <Mail size={17} />
              <input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="you@yourbrand.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </div>
            <div className="field-label-row">
              <label htmlFor="password">Password</label>
              {!creating && <button className="text-button" type="button" title="Password recovery is not available in this setup phase">Forgot password?</button>}
            </div>
            <input
              id="password"
              className="plain-input"
              type="password"
              autoComplete={creating ? 'new-password' : 'current-password'}
              placeholder={creating ? 'At least 12 characters' : 'Enter your password'}
              minLength={creating ? 12 : 1}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
            {error && <p className="form-error" role="alert">{error}</p>}
            <button className="primary-button auth-submit" type="submit" disabled={loading}>
              {loading ? 'One moment…' : creating ? 'Create account' : 'Sign in'}
              {!loading && <ArrowRight size={17} />}
            </button>
          </form>
          <p className="auth-switch">
            {creating ? 'Already have a workspace?' : 'New to Fieldnote?'}{' '}
            <button className="text-button" type="button" onClick={() => { setCreating(!creating); setError(''); }}>
              {creating ? 'Sign in' : 'Create an account'}
            </button>
          </p>
          <p className="auth-privacy">By continuing, you agree to keep your customer data in good hands.</p>
        </div>
      </section>
    </main>
  );
}

function StepPill({ number, label, active, complete }) {
  return (
    <div className={`step-pill ${active ? 'is-active' : ''} ${complete ? 'is-complete' : ''}`}>
      <span className="step-number">{complete ? <Check size={12} /> : number}</span>
      <span>{label}</span>
    </div>
  );
}

function AnalysisSummary({ analysis }) {
  return (
    <aside className="analysis-summary">
      <div className="summary-heading">
        <span className="summary-icon"><ScanSearch size={16} /></span>
        <div><p className="eyebrow">SITE NOTES</p><h3>Brand snapshot</h3></div>
      </div>
      <p className="summary-type">{analysis.business_type}</p>
      <p className="summary-audience">For {analysis.target_audience.toLowerCase()}.</p>
      <div className="summary-divider" />
      <div className="summary-label">VOICE</div>
      <p className="summary-voice">{analysis.brand_tone}</p>
      <div className="summary-label">PRODUCTS</div>
      <div className="product-list">{analysis.products.slice(0, 4).map((product) => <span key={product}>{product}</span>)}</div>
      <div className="summary-label">BRAND COLORS</div>
      <div className="color-swatches">
        {analysis.brand_colors.length ? analysis.brand_colors.slice(0, 5).map((color) => (
          <span key={color} className="color-swatch" style={{ backgroundColor: color }} title={color} />
        )) : <span className="no-colors">No colors detected</span>}
      </div>
      <div className="offer-note">
        <div className="offer-note-icon"><Sparkles size={14} /></div>
        <div>
          <span className="summary-label">OFFER IDEA</span>
          <p>{analysis.suggested_offer.text}</p>
          <small>{analysis.suggested_offer.requires_owner_approval ? 'Needs your approval before use' : 'Found on your website'}</small>
        </div>
      </div>
    </aside>
  );
}

function VariantTile({ variant, selected, onSelect }) {
  return (
    <button className={`variant-tile ${selected ? 'is-selected' : ''}`} type="button" onClick={onSelect}>
      <span className={`variant-letter variant-letter--${variant.label.toLowerCase()}`}>{variant.label}</span>
      <span className="variant-copy">
        <strong>{toneNames[variant.tone] || variant.tone}</strong>
        <span>{variant.config.headline}</span>
      </span>
      {selected && <span className="variant-check"><Check size={14} /></span>}
    </button>
  );
}

function PreviewBrowser({ config, hostname }) {
  const triggerLabel = {
    time_delay: `After ${config.trigger.delay_seconds}s`,
    exit_intent: 'When they’re about to leave',
    scroll_percentage: `At ${config.trigger.scroll_percentage}% scroll`,
  }[config.trigger.type];

  return (
    <div className="browser-frame">
      <div className="browser-bar">
        <div className="browser-dots"><i /><i /><i /></div>
        <div className="browser-address"><Globe2 size={12} /><span>{hostname}</span><ExternalLink size={11} /></div>
        <span className="browser-live"><i /> LIVE PREVIEW</span>
      </div>
      <div className="browser-stage">
        <div className="site-wireframe" aria-hidden="true">
          <div className="wire-nav"><span className="wire-logo" /><span /><span /><span /><span className="wire-cart" /></div>
          <div className="wire-hero"><div className="wire-copy"><i /><i /><i /><b /></div><div className="wire-photo"><span>YOUR BRAND</span></div></div>
          <div className="wire-row"><i /><i /><i /></div>
        </div>
        <div className="preview-dimmer" />
        <div className="preview-overlay">
          <PopupPreview config={config} />
        </div>
      </div>
      <div className="preview-footer">
        <span><MousePointer2 size={14} /> {triggerLabel}</span>
        <span><Clock3 size={14} /> First visit</span>
      </div>
    </div>
  );
}

function Studio({ result, generated, hostname, onBack, onNewSite }) {
  const [selected, setSelected] = useState(generated.variants[0]?.label || 'A');
  const selectedVariant = generated.variants.find((variant) => variant.label === selected) || generated.variants[0];

  return (
    <div className="studio-view">
      <div className="studio-toolbar">
        <button className="back-button" onClick={onBack} type="button"><ArrowLeft size={16} /> New analysis</button>
        <div className="toolbar-right"><span className="draft-badge"><i /> DRAFT</span><button className="icon-button" type="button" title="More options"><ChevronDown size={16} /></button></div>
      </div>
      <div className="studio-heading-row">
        <div>
          <p className="eyebrow">CAMPAIGN CONCEPTS <span>/</span> {hostname.toUpperCase()}</p>
          <h1>Your first hello, <em>three ways.</em></h1>
          <p className="studio-subtitle">We shaped these around {result.analysis.business_type.toLowerCase()} and the people you serve.</p>
        </div>
        <button className="secondary-button new-site-button" onClick={onNewSite} type="button"><Plus size={16} /> Analyze another site</button>
      </div>

      <div className="variant-area">
        <div className="variant-heading"><div><span className="eyebrow">PICK A DIRECTION</span><span className="variant-count">3 concepts</span></div><span className="generated-note"><Sparkles size={14} /> AI-generated, yours to shape</span></div>
        <div className="variant-list">
          {generated.variants.map((variant) => (
            <VariantTile key={variant.label} variant={variant} selected={variant.label === selected} onSelect={() => setSelected(variant.label)} />
          ))}
        </div>
      </div>

      <div className="workbench-grid">
        <AnalysisSummary analysis={result.analysis} />
        <section className="preview-workbench">
          <div className="preview-heading">
            <div><span className="eyebrow">ON YOUR SITE</span><h2>Popup preview</h2></div>
            <span className="variant-live-label"><span className={`variant-letter variant-letter--${selected.toLowerCase()}`}>{selected}</span>{toneNames[selectedVariant.tone] || selectedVariant.tone}</span>
          </div>
          <PreviewBrowser config={selectedVariant.config} hostname={hostname} />
          <div className="preview-footnote"><span><Check size={13} /> Rendered from your popup config</span><span>Changes aren’t saved yet</span></div>
        </section>
      </div>
      <div className="studio-bottom-note"><ArrowDownRight size={15} /> Choose the direction that feels most like you. Editing and publishing are next.</div>
    </div>
  );
}

function Builder({ token, email, onLogout }) {
  const [url, setUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const [busyMessage, setBusyMessage] = useState('');
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [generated, setGenerated] = useState(null);
  const hostname = result ? new URL(result.url).hostname.replace(/^www\./, '') : '';

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    setBusyMessage('Reading your site…');
    try {
      const analysisResult = await analyzeWebsite(url, token);
      setResult(analysisResult);
      setBusyMessage('Finding your first hello…');
      const popupResult = await generatePopups(analysisResult.analysis, token);
      setGenerated(popupResult);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
      setBusyMessage('');
    }
  }

  function reset() {
    setResult(null);
    setGenerated(null);
    setError('');
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup"><span className="brand-mark"><span /></span><span>fieldnote</span></div>
        <div className="workspace-switcher"><span className="workspace-avatar">{email.slice(0, 1).toUpperCase()}</span><span className="workspace-email">{email}</span><ChevronDown size={14} /></div>
        <div className="nav-caption">WORKSPACE</div>
        <nav className="side-nav" aria-label="Main navigation">
          <button type="button" className="nav-item nav-item--active"><LayoutDashboard size={17} /><span>Popup studio</span></button>
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-help"><span className="help-icon"><CircleHelp size={16} /></span><span><strong>Need a hand?</strong><small>Visit the quick guide</small></span><ArrowRight size={14} /></div>
          <button className="account-button" type="button" onClick={onLogout}><span className="account-avatar">{email.slice(0, 1).toUpperCase()}</span><span className="account-copy"><strong>{email.split('@')[0]}</strong><small>Free workspace</small></span><LogOut size={15} /></button>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumbs"><span>Workspace</span><span>/</span><strong>Popup studio</strong></div>
          <div className="topbar-right"><span className="help-status"><i /> All systems normal</span><button type="button" className="icon-button" title="Help"><CircleHelp size={17} /></button><span className="top-avatar">{email.slice(0, 1).toUpperCase()}</span></div>
        </header>

        <div className="main-content">
          {!result ? (
            <section className="create-view">
              <div className="page-heading">
                <div><p className="eyebrow">YOUR POPUP STUDIO</p><h1>Start with your <em>website.</em></h1><p className="page-subtitle">We’ll get to know your brand before we say hello for you.</p></div>
                <div className="stepper"><StepPill number="1" label="Analyze" active={!result} complete={Boolean(result)} /><span className="step-connector" /><StepPill number="2" label="Preview" active={Boolean(result)} complete={Boolean(generated)} /></div>
              </div>

              <div className="create-grid">
                <div className="analyze-panel">
                  <div className="panel-index">01 <span> / SITE ANALYSIS</span></div>
                  <h2>Where should we<br />take a look?</h2>
                  <p className="panel-description">Share your storefront URL. We’ll pick up on your products, voice, and visual details.</p>
                  <form className="analyze-form" onSubmit={submit}>
                    <label htmlFor="website-url">Website URL</label>
                    <div className="url-input-wrap"><Globe2 size={17} /><input id="website-url" type="url" placeholder="https://yourbrand.com" value={url} onChange={(event) => setUrl(event.target.value)} required /></div>
                    {error && <p className="form-error" role="alert">{error}</p>}
                    <button className="primary-button analyze-button" type="submit" disabled={busy}>
                      {busy ? <><span className="button-spinner" /> {busyMessage}</> : <>Analyze my site <ArrowRight size={17} /></>}
                    </button>
                  </form>
                  <div className="panel-trust"><Check size={14} /><span>No changes are made to your website.</span></div>
                </div>
                <div className="process-panel">
                  <div className="process-topline"><span className="eyebrow">THE FIRST HELLO</span><span className="process-stamp">FIELDNOTE / 001</span></div>
                  <div className="process-steps">
                    <div className="process-step"><span className="process-icon process-icon--green"><ScanSearch size={18} /></span><div><strong>Notice the details</strong><p>We look for your products, visual cues, and the way you speak.</p></div><span className="process-number">01</span></div>
                    <div className="process-line" />
                    <div className="process-step"><span className="process-icon process-icon--yellow"><WandSparkles size={18} /></span><div><strong>Find your voice</strong><p>Three signup ideas, each with a different kind of welcome.</p></div><span className="process-number">02</span></div>
                    <div className="process-line" />
                    <div className="process-step"><span className="process-icon process-icon--coral"><MousePointer2 size={18} /></span><div><strong>See it in context</strong><p>Choose a direction and preview it on a storefront.</p></div><span className="process-number">03</span></div>
                  </div>
                  <div className="process-bottom"><span>Good design starts with paying attention.</span><span className="process-doodle">✳</span></div>
                </div>
              </div>
              <div className="create-footer"><span>FIELDNOTE STUDIO</span><span>Thoughtful first impressions, by design.</span><span>V 0.1</span></div>
            </section>
          ) : generated ? (
            <Studio result={result} generated={generated} hostname={hostname} onBack={reset} onNewSite={reset} />
          ) : (
            <div className="analysis-complete">
              <div className="analysis-success-icon"><Check size={20} /></div>
              <p className="eyebrow">SITE ANALYZED</p>
              <h2>Your brand notes are ready.</h2>
              <p>We found {result.analysis.products.length} product categories and {result.analysis.brand_colors.length} brand colors for {hostname}.</p>
              <button className="primary-button" onClick={async () => {
                setBusy(true);
                setError('');
                try { setGenerated(await generatePopups(result.analysis, token)); }
                catch (requestError) { setError(requestError.message); }
                finally { setBusy(false); }
              }} type="button" disabled={busy}>{busy ? 'Creating concepts…' : 'Generate popup concepts'} <ArrowRight size={17} /></button>
              {error && <p className="form-error" role="alert">{error}</p>}
              <button className="text-button analysis-back" type="button" onClick={reset}>Try another website</button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default function App() {
  const [token, setAuthToken] = useState(() => getToken());
  const [email, setEmail] = useState(() => sessionStorage.getItem('fieldnote_email') || '');

  function handleAuthenticated(nextToken, nextEmail) {
    setToken(nextToken);
    setEmail(nextEmail);
    sessionStorage.setItem('fieldnote_email', nextEmail);
  }

  function logout() {
    clearToken();
    sessionStorage.removeItem('fieldnote_email');
    setToken(null);
    setEmail('');
  }

  return token
    ? <Builder token={token} email={email} onLogout={logout} />
    : <AuthScreen onAuthenticated={handleAuthenticated} />;
}