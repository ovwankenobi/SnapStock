import SegmentedControl from "../../components/SegmentedControl";
import { useAuth } from "./AuthContext";

export default function LanguageToggle({ className }) {
  const { language, setLanguage, t } = useAuth();

  return (
    <div className={className}>
      <SegmentedControl
        options={[
          { value: "en", label: t("language.english") },
          { value: "tl", label: t("language.tagalog") },
        ]}
        value={language}
        onChange={setLanguage}
      />
    </div>
  );
}
