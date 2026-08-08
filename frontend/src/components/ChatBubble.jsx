import styles from "./chat.module.css";

export default function ChatBubble({ text, align = "start" }) {
  return (
    <div className={`${styles["bubble-row"]} ${styles[`bubble-row-${align}`]}`}>
      <div className={`${styles.bubble} ${styles[`bubble-${align}`]}`}>{text}</div>
    </div>
  );
}
