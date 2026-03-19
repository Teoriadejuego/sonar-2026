interface ConsentModalProps {
  isOpen: boolean;
  title: string;
  sections: {
    title: string;
    body: string;
  }[];
  closeLabel: string;
  onClose: () => void;
}

export function ConsentModal({
  isOpen,
  title,
  sections,
  closeLabel,
  onClose,
}: ConsentModalProps) {
  if (!isOpen) {
    return null;
  }

  return (
    <div className="sonar-modal-backdrop" onClick={onClose}>
      <div
        className="sonar-modal"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-black/10 px-5 py-4 sm:px-6">
          <h3 className="pr-4 text-[1.35rem] font-black leading-tight text-slate-950">
            {title}
          </h3>
          <button
            type="button"
            onClick={onClose}
            aria-label={closeLabel}
            className="sonar-secondary-button min-h-0 px-3 py-2 text-[0.72rem]"
          >
            X
          </button>
        </div>

        <div className="sonar-modal-scroll px-5 py-5 sm:px-6">
          {sections.map((section) => (
            <section key={section.title} className="sonar-modal-section space-y-2">
              <h4 className="editorial-eyebrow">
                {section.title}
              </h4>
              <p className="editorial-small whitespace-pre-line text-slate-700">
                {section.body}
              </p>
            </section>
          ))}
        </div>

        <div className="border-t border-black/10 px-5 py-4 sm:px-6">
          <button
            type="button"
            onClick={onClose}
            className="sonar-secondary-button w-full"
          >
            {closeLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
