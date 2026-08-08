const PATHS = {
  home: <path d="M4 11.5L12 4l8 7.5M6 10v9a1 1 0 001 1h4v-6h2v6h4a1 1 0 001-1v-9" fill="none" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" />,
  box: <path d="M3 8l9-4 9 4-9 4-9-4zM3 8v8l9 4 9-4V8" fill="none" strokeWidth="1.9" strokeLinejoin="round" />,
  chat: <path d="M4 5h16v10H8l-4 4V5z" fill="none" strokeWidth="1.9" strokeLinejoin="round" />,
  user: <><circle cx="12" cy="8" r="4" fill="none" strokeWidth="1.8" /><path d="M4 20c0-4 4-6 8-6s8 2 8 6" fill="none" strokeWidth="1.8" strokeLinecap="round" /></>,
  receipt: <path d="M6 2h12v20l-3-2-3 2-3-2-3 2V2zM9 7h6M9 11h6M9 15h4" fill="none" strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round" />,
  back: <path d="M15 4l-8 8 8 8" fill="none" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />,
  close: <path d="M5 5l14 14M19 5L5 19" fill="none" strokeWidth="2.2" strokeLinecap="round" />,
  plus: <path d="M12 5v14M5 12h14" fill="none" strokeWidth="2.4" strokeLinecap="round" />,
  camera: <><path d="M3 7h18v13H3zM8 7l1.5-3h5L16 7" fill="none" strokeWidth="1.6" strokeLinejoin="round" /><circle cx="12" cy="13.5" r="3.5" fill="none" strokeWidth="1.6" /></>,
  send: <path d="M3 11l18-8-8 18-2-8-8-2z" />,
  search: <path d="M11 4a7 7 0 105 12l5 5" fill="none" strokeWidth="1.8" strokeLinecap="round" />,
  warning: <path d="M12 3l10 18H2L12 3zM12 10v4M12 17.5v.1" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />,
  chart: <><rect x="4" y="12" width="3.5" height="8" /><rect x="10.25" y="7" width="3.5" height="13" /><rect x="16.5" y="3" width="3.5" height="17" /></>,
  check: <path d="M4 12l5 5L20 6" fill="none" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />,
  logout: <><path d="M9 4H5a1 1 0 00-1 1v14a1 1 0 001 1h4" fill="none" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /><path d="M13 8l5 4-5 4M18 12H9" fill="none" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></>,
  sun: <><circle cx="12" cy="12" r="4" fill="none" strokeWidth="1.8" /><path d="M12 2v2.5M12 19.5V22M4.2 4.2l1.8 1.8M18 18l1.8 1.8M2 12h2.5M19.5 12H22M4.2 19.8L6 18M18 6l1.8-1.8" fill="none" strokeWidth="1.8" strokeLinecap="round" /></>,
  moon: <path d="M20.5 14.7A8.5 8.5 0 119.3 3.5a6.8 6.8 0 0011.2 11.2z" fill="none" strokeWidth="1.6" strokeLinejoin="round" />,
  pin: <path d="M12 2l2.2 6.8H21l-5.6 4.1 2.2 6.8L12 15.6l-5.6 4.1 2.2-6.8L3 8.8h6.8z" fill="none" strokeWidth="1.6" strokeLinejoin="round" />,
};

export default function Icon({ name, size = 18, color = "currentColor" }) {
  const path = PATHS[name];
  if (!path) return null;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" stroke={color} fill={color}>
      {path}
    </svg>
  );
}
