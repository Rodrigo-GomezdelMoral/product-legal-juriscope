import { ExternalLink } from "lucide-react";
import { useState } from "react";
import type { Citation, Refusal, Version } from "./api";

const REASONS: Record<string, [string, string]> = {
  case_law: ["Juriscope answers from the text of the Criminal Code, not from case law.", "Ask what the Code says about the offence, and check the case law in the firm's database."],
  other_law: ["The question concerns another law, and Juriscope covers only the Criminal Code.", "Ask about the offence as the Criminal Code defines it."],
  not_legal: ["This is not a question about the Criminal Code.", "Ask about an offence, a penalty or a rule of the Code."],
  no_evidence: ["No article of the Criminal Code supports an answer to this question.", "Name the offence or the article, or state the question in other words."],
  content_filter: ["The content safety filter stopped this question.", "State the question in neutral legal terms."],
};

function Text({ version, label }: { version: Version; label?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="version">
      {label && <p className="label">{label}</p>}
      <p className="badge">
        In force since {version.in_force} · {version.norm}
      </p>
      <p className={open ? "text" : "text clamped"} lang="es">
        {version.text}
      </p>
      <button className="link" aria-expanded={open} onClick={() => setOpen(!open)}>
        {open ? "Show less" : "Show full article"}
      </button>
    </div>
  );
}

export function ArticleCard({ citation, number, anchor, date }: { citation: Citation; number: number; anchor: string; date: string | null }) {
  const { title, version, current, repealed, see_also, url } = citation;
  return (
    <article className="card" id={anchor} aria-label={`${number}. ${title}`}>
      <h3>
        <span className="number">{number}</span> {title}
      </h3>
      <div className={current ? "versions" : undefined}>
        <Text version={version} label={current ? `Applies on ${date}` : undefined} />
        {current && <Text version={current} label="In force today" />}
      </div>
      {repealed && <p className="label">Repealed since {repealed}</p>}
      {see_also.length > 0 && (
        <p className="also">
          See also:{" "}
          {see_also.map((item, index) => (
            <span key={item.block_id}>
              {index > 0 && ", "}
              <a href={item.url} target="_blank" rel="noreferrer">
                {item.title}
              </a>
            </span>
          ))}
        </p>
      )}
      <p className="source">
        <a href={url} target="_blank" rel="noreferrer">
          Official text on boe.es <ExternalLink size={14} aria-hidden />
        </a>
        <span lang="es">Fuente de los datos: Agencia Estatal Boletín Oficial del Estado</span>
      </p>
    </article>
  );
}

export function RefusalCard({ refusal }: { refusal: Refusal }) {
  const [reason, suggestion] = REASONS[(refusal.reason === "out_of_scope" && refusal.scope) || refusal.reason] ?? REASONS.not_legal;
  return (
    <div className="card refusal">
      <h3>Juriscope does not answer this question</h3>
      <p>{reason}</p>
      <p className="label">{suggestion}</p>
    </div>
  );
}
