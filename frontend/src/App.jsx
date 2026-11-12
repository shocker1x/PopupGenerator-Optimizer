import { useEffect, useState } from 'react';
import {
  ArrowDownRight,
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronDown,
  CircleHelp,
  Clock3,
  Copy,
  Download,
  ExternalLink,
  Globe2,
  ImagePlus,
  LayoutDashboard,
  LogOut,
  Mail,
  MousePointer2,
  Plus,
  Save,
  ScanSearch,
  Sparkles,
  Trash2,
  Upload,
  WandSparkles,
} from 'lucide-react';
import PopupPreview from './components/PopupPreview.jsx';
import {
  analyzeWebsite,
  authenticate,
  clearToken,
  createCampaign,
  deleteCampaignSubscriber,
  exportCampaignSubscribers,
  getCampaignAnalytics,
  getCampaignSubscribers,
  generatePopups,
  getToken,
  publishCampaign,
  regeneratePopupVersion,
  setToken,
  updatePopupVersion,
  uploadPopupImage,
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

function PopupEditor({ config, onChange, onUploadImage, uploading }) {
  function updateTheme(field, value) {
    onChange({ ...config, theme: { ...config.theme, [field]: value } });
  }

  function updateTrigger(field, value) {
    onChange({
      ...config,
      trigger: {
        ...config.trigger,
        [field]: field === 'type' ? value : Number(value),
      },
    });
  }

  return (
    <div className="editor-grid">
      <label className="editor-field editor-field--wide">
        <span>Headline</span>
        <input maxLength={90} value={config.headline} onChange={(event) => onChange({ ...config, headline: event.target.value })} />
        <small>{config.headline.length}/90</small>
      </label>
      <label className="editor-field editor-field--wide">
        <span>Description</span>
        <textarea maxLength={240} rows={3} value={config.description} onChange={(event) => onChange({ ...config, description: event.target.value })} />
        <small>{config.description.length}/240</small>
      </label>
      <label className="editor-field">
        <span>Button text</span>
        <input maxLength={40} value={config.cta} onChange={(event) => onChange({ ...config, cta: event.target.value })} />
      </label>
      <label className="editor-field">
        <span>Trigger</span>
        <select value={config.trigger.type} onChange={(event) => updateTrigger('type', event.target.value)}>
          <option value="time_delay">Time delay</option>
          <option value="exit_intent">Exit intent</option>
          <option value="scroll_percentage">Scroll depth</option>
        </select>
      </label>
      {config.trigger.type === 'time_delay' && (
        <label className="editor-field"><span>Delay (seconds)</span><input type="number" min="1" max="120" value={config.trigger.delay_seconds} onChange={(event) => updateTrigger('delay_seconds', event.target.value)} /></label>
      )}
      {config.trigger.type === 'scroll_percentage' && (
        <label className="editor-field"><span>Scroll depth (%)</span><input type="number" min="10" max="95" value={config.trigger.scroll_percentage} onChange={(event) => updateTrigger('scroll_percentage', event.target.value)} /></label>
      )}
      <div className="editor-field editor-field--wide">
        <span>Popup colors</span>
        <div className="color-edit-row">
          {[
            ['background_color', 'Background'],
            ['text_color', 'Text'],
            ['accent_color', 'Button'],
          ].map(([field, label]) => (
            <label key={field} className="color-edit-control"><input type="color" value={config.theme[field]} onChange={(event) => updateTheme(field, event.target.value)} /><span>{label}</span></label>
          ))}
        </div>
      </div>
      <div className="editor-field editor-field--wide">
        <span>Artwork</span>
        <div className="image-edit-row">
          {config.image ? <img src={config.image} alt="Current popup artwork" /> : <span className="image-empty"><ImagePlus size={17} /> No image selected</span>}
          <label className="secondary-button upload-button">
            {uploading ? <span className="button-spinner button-spinner--dark" /> : <Upload size={15} />}
            {uploading ? 'Uploading…' : config.image ? 'Replace image' : 'Upload image'}
            <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => onUploadImage(event.target.files?.[0])} disabled={uploading} />
          </label>
          {config.image && <button className="text-button" type="button" onClick={() => onChange({ ...config, image: null })}>Remove</button>}
        </div>
        <small>JPEG, PNG, or WebP. Maximum 5 MB.</small>
      </div>
    </div>
  );
}

function Studio({ result, campaign, generated, hostname, token, onBack, onNewSite }) {
  const [variants, setVariants] = useState(generated.variants);
  const [campaignStatus, setCampaignStatus] = useState(campaign.status);
  const [selected, setSelected] = useState(generated.variants[0]?.label || 'A');
  const selectedVariant = variants.find((variant) => variant.label === selected) || variants[0];
  const [config, setConfig] = useState(selectedVariant.config);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [instruction, setInstruction] = useState('');
  const [error, setError] = useState('');
  const [publishResult, setPublishResult] = useState(null);
  const [copied, setCopied] = useState(false);
  const [analytics, setAnalytics] = useState(null);
  const [subscribers, setSubscribers] = useState([]);
  const [analyticsBusy, setAnalyticsBusy] = useState(false);
  const [analyticsError, setAnalyticsError] = useState('');

  async function refreshAnalytics() {
    setAnalyticsBusy(true);
    setAnalyticsError('');
    try {
      const [report, subscriberRows] = await Promise.all([
        getCampaignAnalytics(campaign.id, token),
        getCampaignSubscribers(campaign.id, token),
      ]);
      setAnalytics(report);
      setSubscribers(subscriberRows);
    } catch (requestError) {
      setAnalyticsError(requestError.message);
    } finally {
      setAnalyticsBusy(false);
    }
  }

  useEffect(() => {
    if (campaignStatus === 'published') void refreshAnalytics();
  }, [campaignStatus, campaign.id, token]);

  function selectVariant(label) {
    const next = variants.find((variant) => variant.label === label);
    if (!next) return;
    setSelected(label);
    setConfig(next.config);
    setDirty(false);
    setError('');
  }

  function changeConfig(nextConfig) {
    setConfig(nextConfig);
    setDirty(true);
  }

  function replaceVariantConfig(nextConfig) {
    setConfig(nextConfig);
    setVariants((current) => current.map((variant) => (
      variant.label === selected ? { ...variant, config: nextConfig } : variant
    )));
    setDirty(false);
  }

  async function saveChanges() {
    setBusy(true);
    setError('');
    try {
      const version = selectedVariant.version_id;
      const saved = await updatePopupVersion(version, config, token);
      replaceVariantConfig(saved.config);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  async function regenerate() {
    if (!instruction.trim()) return;
    setBusy(true);
    setError('');
    try {
      const versionId = selectedVariant.version_id;
      if (dirty) {
        const draft = await updatePopupVersion(versionId, config, token);
        replaceVariantConfig(draft.config);
      }
      const saved = await regeneratePopupVersion(versionId, instruction.trim(), token);
      replaceVariantConfig(saved.config);
      setInstruction('');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleUpload(file) {
    if (!file) return;
    setError('');
    if (file.size > 5 * 1024 * 1024) {
      setError('Choose an image that is 5 MB or smaller.');
      return;
    }
    setUploading(true);
    try {
      const uploaded = await uploadPopupImage(file, token);
      changeConfig({ ...config, image: uploaded.url });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setUploading(false);
    }
  }

  async function publish() {
    setBusy(true);
    setError('');
    try {
      let versionId = selectedVariant.version_id;
      if (dirty) {
        const saved = await updatePopupVersion(versionId, config, token);
        replaceVariantConfig(saved.config);
      }
      const publishResponse = await publishCampaign(campaign.id, versionId, token);
      setPublishResult(publishResponse);
      setCampaignStatus('published');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  async function copySnippet() {
    await navigator.clipboard.writeText(publishResult.embed_snippet);
    setCopied(true);
  }

  async function exportSubscribers() {
    try {
      const blob = await exportCampaignSubscribers(campaign.id, token);
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `campaign-${campaign.id}-subscribers.csv`;
      link.click();
      URL.revokeObjectURL(link.href);
    } catch (requestError) {
      setAnalyticsError(requestError.message);
    }
  }

  async function removeSubscriber(subscriberId) {
    const subscriber = subscribers.find((item) => item.id === subscriberId);
    if (!subscriber || !window.confirm(`Permanently delete ${subscriber.email}?`)) return;
    try {
      await deleteCampaignSubscriber(campaign.id, subscriberId, token);
      setSubscribers((current) => current.filter((subscriber) => subscriber.id !== subscriberId));
      await refreshAnalytics();
    } catch (requestError) {
      setAnalyticsError(requestError.message);
    }
  }

  return (
    <div className="studio-view">
      <div className="studio-toolbar">
        <button className="back-button" onClick={onBack} type="button"><ArrowLeft size={16} /> New analysis</button>
        <div className="toolbar-right"><span className={`draft-badge ${campaignStatus === 'published' ? 'draft-badge--published' : ''}`}><i /> {campaignStatus.toUpperCase()}</span><button className="icon-button" type="button" title="More options"><ChevronDown size={16} /></button></div>
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
          {variants.map((variant) => (
            <VariantTile key={variant.label} variant={variant} selected={variant.label === selected} onSelect={() => selectVariant(variant.label)} />
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
          <PreviewBrowser config={config} hostname={hostname} />
          <div className="preview-footnote"><span><Check size={13} /> Rendered from your popup config</span><span>{dirty ? 'Unsaved changes' : 'Saved draft'}</span></div>

          <div className="editor-section">
            <div className="editor-section-heading"><div><span className="eyebrow">MAKE IT YOURS</span><h3>Edit this direction</h3></div><button className="primary-button save-button" type="button" onClick={saveChanges} disabled={!dirty || busy}>{busy && !publishResult ? 'Saving…' : <><Save size={14} /> Save changes</>}</button></div>
            <PopupEditor config={config} onChange={changeConfig} onUploadImage={handleUpload} uploading={uploading} />
            <div className="regenerate-box">
              <span className="regenerate-icon"><WandSparkles size={16} /></span>
              <div className="regenerate-content"><label htmlFor="regenerate-instruction">Ask for a focused change</label><div className="regenerate-row"><input id="regenerate-instruction" placeholder="e.g. Make the headline more understated" maxLength={500} value={instruction} onChange={(event) => setInstruction(event.target.value)} /><button className="secondary-button" type="button" onClick={regenerate} disabled={busy || instruction.trim().length < 3}><WandSparkles size={14} /> Regenerate</button></div><small>Only copy, colors, trigger, and image fields may change.</small></div>
            </div>
            {error && <p className="form-error" role="alert">{error}</p>}
            <div className="publish-row"><div><strong>Ready to put it to work?</strong><small>Publishing makes this direction the campaign default.</small></div><button className="primary-button publish-button" type="button" onClick={publish} disabled={busy}>{busy ? 'Publishing…' : <>Publish popup <ArrowRight size={16} /></>}</button></div>
          </div>
          {campaignStatus === 'published' && (
            <section className="analytics-panel">
              <div className="analytics-heading">
                <div><span className="eyebrow">CAMPAIGN PERFORMANCE</span><h3>How it’s landing</h3></div>
                <div className="analytics-actions"><button className="secondary-button" type="button" onClick={refreshAnalytics} disabled={analyticsBusy}>{analyticsBusy ? 'Refreshing…' : 'Refresh'}</button><button className="secondary-button" type="button" onClick={exportSubscribers}><Download size={14} /> Export CSV</button></div>
              </div>
              {analyticsError && <p className="form-error" role="alert">{analyticsError}</p>}
              {analytics ? (
                <>
                  <div className="metric-row">
                    <div className="metric-cell"><span>Impressions</span><strong>{analytics.impressions}</strong></div>
                    <div className="metric-cell"><span>Signups</span><strong>{analytics.submissions}</strong></div>
                    <div className="metric-cell"><span>Conversion</span><strong>{analytics.conversion_rate}%</strong></div>
                    <div className="metric-cell"><span>Dismissals</span><strong>{analytics.versions.reduce((sum, item) => sum + item.dismissals, 0)}</strong></div>
                  </div>
                  <div className="analytics-table-wrap">
                    <table className="analytics-table"><thead><tr><th>Variant</th><th>Impressions</th><th>Signups</th><th>Conversion</th><th>Dismissals</th></tr></thead><tbody>
                      {analytics.versions.map((row) => <tr key={row.version_id}><td><span className={`variant-letter variant-letter--${row.label.toLowerCase()}`}>{row.label}</span></td><td>{row.impressions}</td><td>{row.submissions}</td><td>{row.conversion_rate}%</td><td>{row.dismissals}</td></tr>)}
                    </tbody></table>
                  </div>
                  <div className="subscriber-heading"><div><strong>Subscribers</strong><span>{subscribers.length}{subscribers.length === 500 ? '+' : ''} shown</span></div></div>
                  {subscribers.length ? <div className="subscriber-list">{subscribers.map((subscriber) => <div className="subscriber-row" key={subscriber.id}><span className="subscriber-avatar">{subscriber.email.slice(0, 1).toUpperCase()}</span><div className="subscriber-copy"><strong>{subscriber.email}</strong><small>Consented {new Date(subscriber.consented_at).toLocaleDateString()}</small></div><button className="icon-button delete-subscriber" type="button" title="Delete subscriber" onClick={() => removeSubscriber(subscriber.id)}><Trash2 size={14} /></button></div>)}</div> : <p className="empty-subscribers">No subscribers yet. New signups will appear here.</p>}
                </>
              ) : !analyticsBusy && !analyticsError ? <p className="empty-subscribers">Performance data will appear after the popup is shown.</p> : null}
            </section>
          )}
        </section>
      </div>
      <div className="studio-bottom-note"><ArrowDownRight size={15} /> Your draft is yours to shape. Publish when the welcome feels right.</div>

      {publishResult && (
        <div className="modal-backdrop" role="presentation" onClick={(event) => { if (event.target === event.currentTarget) setPublishResult(null); }}>
          <section className="publish-modal" role="dialog" aria-modal="true" aria-labelledby="publish-title">
            <div className="publish-success-mark"><Check size={20} /></div>
            <p className="eyebrow">CAMPAIGN PUBLISHED</p>
            <h2 id="publish-title">Your popup is ready to travel.</h2>
            <p>Add this embed snippet to your site to show the selected popup.</p>
            <div className="snippet-box"><code>{publishResult.embed_snippet}</code><button className="icon-button" type="button" onClick={copySnippet} title="Copy embed snippet">{copied ? <Check size={15} /> : <Copy size={15} />}</button></div>
            <button className="primary-button modal-done" type="button" onClick={() => setPublishResult(null)}>Done</button>
          </section>
        </div>
      )}
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
  const [campaign, setCampaign] = useState(null);
  const hostname = result ? new URL(result.url).hostname.replace(/^www\./, '') : '';

  async function saveGeneratedCampaign(analysisResult, popupResult) {
    const savedCampaign = await createCampaign(
      analysisResult.website_id,
      `${new URL(analysisResult.url).hostname.replace(/^www\./, '')} welcome popup`,
      popupResult.variants,
      token,
    );
    const variants = popupResult.variants.map((variant) => {
      const savedVersion = savedCampaign.versions.find((item) => item.label === variant.label);
      return { ...variant, version_id: savedVersion.id, config: savedVersion.config };
    });
    setCampaign(savedCampaign);
    setGenerated({ variants });
  }

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
      await saveGeneratedCampaign(analysisResult, popupResult);
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
    setCampaign(null);
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
            <Studio result={result} campaign={campaign} generated={generated} hostname={hostname} token={token} onBack={reset} onNewSite={reset} />
          ) : (
            <div className="analysis-complete">
              <div className="analysis-success-icon"><Check size={20} /></div>
              <p className="eyebrow">SITE ANALYZED</p>
              <h2>Your brand notes are ready.</h2>
              <p>We found {result.analysis.products.length} product categories and {result.analysis.brand_colors.length} brand colors for {hostname}.</p>
              <button className="primary-button" onClick={async () => {
                setBusy(true);
                setError('');
                try {
                  const popupResult = await generatePopups(result.analysis, token);
                  await saveGeneratedCampaign(result, popupResult);
                }
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