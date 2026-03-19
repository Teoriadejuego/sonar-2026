import { LanguageSwitcher } from "./LanguageSwitcher";

export function ScreenFrame({
  children,
  contentClassName = "min-h-[calc(100%-3rem)]",
  hideLanguageSwitcher = false,
}: {
  children: React.ReactNode;
  contentClassName?: string;
  hideLanguageSwitcher?: boolean;
}) {
  return (
    <div className="webapp-container text-slate-950">
      {!hideLanguageSwitcher && (
        <div className="screen-frame-header">
          <LanguageSwitcher />
        </div>
      )}
      <div className={`screen-frame-content ${contentClassName}`}>{children}</div>
    </div>
  );
}
