import Icon from "./Icon";
import styles from "./chat.module.css";

export default function ChatComposer({ value, onChange, onSend, placeholder = "Type a message…" }) {
  const submit = () => {
    if (value.trim()) onSend();
  };
  return (
    <div className={styles.composer}>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
        onKeyDown={(e) => e.key === "Enter" && submit()}
      />
      <button type="button" onClick={submit} aria-label="Send message">
        <Icon name="send" size={18} color="var(--color-on-primary)" />
      </button>
    </div>
  );
}
