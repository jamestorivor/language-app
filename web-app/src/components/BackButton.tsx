import { useLocation, useNavigate } from "react-router";
import { useLanguage } from "../i18n-context";

export default function BackButton() {
  const { t } = useLanguage();
  const location = useLocation();
  const navigate = useNavigate();
  if (["/", "/podcasts", "/study", "/podcasts/add"].includes(location.pathname)) return null;

  const fallback = location.pathname.startsWith("/study/") ? "/study"
    : location.pathname.startsWith("/podcasts/") ? "/podcasts" : "/";
  return <button type="button" onClick={() => {
    if (typeof window.history.state?.idx === "number" && window.history.state.idx > 0) void navigate(-1);
    else void navigate(fallback, { replace: true });
  }} className="mb-6 inline-flex items-center gap-2 rounded-lg text-sm font-semibold text-stone-600 hover:text-emerald-900 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-emerald-800">
    <span aria-hidden="true">←</span>{t("Back")}
  </button>;
}
