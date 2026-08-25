export default function XAIHighlight({ tokens = [] }) {
  if (!tokens.length) return null;
  const max = Math.max(...tokens.map(t => Math.abs(t.score)));
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
      {tokens.map((t, i) => {
        const alpha = max > 0 ? 0.08 + (Math.abs(t.score) / max) * 0.4 : 0.1;
        return (
          <span key={i} style={{ padding: '3px 10px', borderRadius: 6, fontSize: '0.8rem', background: `rgba(99,132,255,${alpha})`, color: '#f1f5f9' }}>
            {t.token}
          </span>
        );
      })}
    </div>
  );
}
