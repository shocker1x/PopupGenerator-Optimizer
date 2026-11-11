import { Check, X } from 'lucide-react';

const fontFamilies = {
  system: 'Arial, sans-serif',
  inter: 'Inter, sans-serif',
  roboto: 'Roboto, sans-serif',
  georgia: 'Georgia, serif',
  montserrat: 'Montserrat, sans-serif',
  lato: 'Lato, sans-serif',
};

export default function PopupPreview({ config, compact = false }) {
  const style = {
    '--popup-bg': config.theme.background_color,
    '--popup-ink': config.theme.text_color,
    '--popup-accent': config.theme.accent_color,
    '--popup-radius': `${config.theme.border_radius}px`,
    '--popup-font': fontFamilies[config.theme.font] || 'sans-serif',
  };

  return (
    <article className={`popup-card ${compact ? 'popup-card--compact' : ''}`} style={style}>
      <button className="popup-dismiss" type="button" aria-label="Close popup preview">
        <X size={compact ? 12 : 15} />
      </button>
      {config.image && (
        <div className="popup-image-wrap">
          <img src={config.image} alt="Popup campaign artwork" className="popup-image" />
        </div>
      )}
      {config.offer && !config.offer.requires_owner_approval && (
        <span className="popup-offer">{config.offer.text}</span>
      )}
      <h3 className="popup-headline">{config.headline}</h3>
      <p className="popup-description">{config.description}</p>
      <form className="popup-form" onSubmit={(event) => event.preventDefault()}>
        <input aria-label={config.email_placeholder} placeholder={config.email_placeholder} />
        <button type="submit">{config.cta}</button>
      </form>
      <p className="popup-consent"><Check size={11} /> {config.consent_text}</p>
    </article>
  );
}