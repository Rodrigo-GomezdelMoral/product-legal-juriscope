import "@fontsource/inter/latin-400.css";
import "@fontsource/inter/latin-600.css";
import "./styles.css";
import { ArrowUp, Check, Copy, LoaderCircle, LogOut, Menu, MessageSquare, PlayCircle, Search, SquarePen, ThumbsDown, ThumbsUp, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import Markdown from "react-markdown";
import { answered, api, DEMO, RUNS, type Answer, type Me, type Meta, type Phase, type Run, type Summary, type Turn } from "./api";
import { ArticleCard, RefusalCard } from "./Article";

const BRAND = `${import.meta.env.BASE_URL}brand/`;
const SUGGESTIONS = [
  "What is the penalty for reckless homicide?",
  "¿Qué decía el artículo 139 sobre el asesinato en mayo de 2014?",
  "¿Cuándo prescribe un delito de estafa?",
  "What does the Criminal Code say about self-defence?",
];
const STEPS: Phase["step"][] = ["analysing", "searching", "reading", "drafting", "verifying"];
type Shown = { question: string; phase: Phase["step"]; articles?: number; turn?: Turn; error?: string };
type Item = { key: string; label: string; go: () => void; remove?: () => void };

function Progress({ shown }: { shown: Shown }) {
  const at = STEPS.indexOf(shown.phase);
  const labels = ["Analysing the question", "Searching the Code", `Reading ${shown.articles ?? ""} articles`, "Drafting", "Verifying citations"];
  return (
    <p className="status progress" role="status">
      {labels.map((label, index) => (
        <span key={label} className={index < at ? "done" : index === at ? "now" : undefined}>
          {index < at && <Check size={14} aria-hidden />}
          {index === at && <LoaderCircle size={14} className="spin" aria-hidden />}
          {label.replace("  ", " ")}
        </span>
      ))}
    </p>
  );
}

function Actions({ turn, answer }: { turn: Turn; answer: Answer }) {
  const [vote, setVote] = useState<"up" | "down">();
  const [copied, setCopied] = useState(false);
  const send = (value: "up" | "down" | "copy") => api.feedback(turn.id, value).catch(() => undefined);
  const rate = (value: "up" | "down") => vote !== value && (setVote(value), send(value));
  const sources = answer.citations.map((item, index) => `[${index + 1}] ${item.title}, ${item.version.norm}: ${item.url}`);
  const copy = () => navigator.clipboard.writeText([answer.text, ...sources].join("\n\n")).then(() => (setCopied(true), send("copy")), () => setCopied(false));
  return (
    <div className="actions">
      <button className="icon" aria-label={copied ? "Copied" : "Copy the answer"} onClick={copy}>
        {copied ? <Check size={16} /> : <Copy size={16} />}
      </button>
      <button className="icon" aria-label="Helpful" aria-pressed={vote === "up"} onClick={() => rate("up")}>
        <ThumbsUp size={16} />
      </button>
      <button className="icon" aria-label="Not helpful" aria-pressed={vote === "down"} onClick={() => rate("down")}>
        <ThumbsDown size={16} />
      </button>
    </div>
  );
}

function Outcome({ turn, meta }: { turn: Turn; meta?: Meta }) {
  const outcome = turn.outcome;
  if (!answered(outcome)) return <RefusalCard refusal={outcome} />;
  const anchor = (number: string | number) => `c${turn.id}-${number}`;
  return (
    <>
      <p className="sr-only" role="status">
        Answer ready, {outcome.citations.length} cited articles
      </p>
      <div className="answer" lang={outcome.language}>
        <Markdown disallowedElements={["img"]} urlTransform={(url) => (url.startsWith("#") ? url : null)}>
          {outcome.text.replace(/\[(\d+)\]/g, (_, number: string) => `[${number}](#${anchor(number)})`)}
        </Markdown>
      </div>
      {outcome.citations.map((citation, index) => (
        <ArticleCard key={citation.block_id} citation={citation} number={index + 1} anchor={anchor(index + 1)} date={outcome.facts_date} />
      ))}
      {meta && (
        <footer className="notice">
          <span lang="es">{meta.notice}</span> Last updated {meta.updated}. For the firm's lawyers. Not legal advice.
        </footer>
      )}
      <Actions turn={turn} answer={outcome} />
    </>
  );
}

function App() {
  const [me, setMe] = useState<Me>();
  const [meta, setMeta] = useState<Meta>();
  const [summaries, setSummaries] = useState<Summary[]>([]);
  const [shown, setShown] = useState<Shown[]>([]);
  const [conversation, setConversation] = useState<string>();
  const [active, setActive] = useState("");
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState("");
  const [filter, setFilter] = useState<string>();
  const [menu, setMenu] = useState(false);
  const [failure, setFailure] = useState<string>();
  const generation = useRef(0);
  const end = useRef<HTMLDivElement>(null);
  const fail = (error: unknown) => setFailure((error as Error).message);
  const refresh = () => void (DEMO || api.conversations().then(setSummaries, fail));

  useEffect(() => {
    api.me().then(setMe, fail);
    api.meta().then(setMeta, fail);
    refresh();
    const run = RUNS.find((item) => new URLSearchParams(location.search).get("run") === item.id);
    if (run) play(run);
  }, []);
  useEffect(() => void end.current?.scrollIntoView({ block: "end" }), [shown.length]);

  function reset(key = "", id?: string, turns: Shown[] = []) {
    generation.current += 1;
    setBusy(false);
    setShown(turns);
    setActive(key);
    setConversation(id);
    setMenu(false);
    setFailure(undefined);
    if (DEMO) history.replaceState(null, "", location.pathname);
  }

  async function ask(question: string, id = conversation) {
    const mine = generation.current;
    const update = (patch: Partial<Shown>) => mine === generation.current && setShown((list) => list.map((item, index) => (index === list.length - 1 ? { ...item, ...patch } : item)));
    setBusy(true);
    setShown((list) => [...list, { question, phase: "analysing" }]);
    let ended = false;
    try {
      for await (const item of api.ask(id, question)) {
        if (mine !== generation.current) return;
        ended ||= item.event !== "phase";
        if (item.event === "phase") update({ phase: item.data.step, ...(item.data.articles !== null && { articles: item.data.articles }) });
        else if (item.event === "error") update({ error: item.data.detail });
        else if (!DEMO) (update({ turn: item.data.turn }), setConversation(item.data.conversation_id), setActive(item.data.conversation_id));
        else update({ turn: item.data.turn });
      }
      if (!ended) update({ error: "The answer was interrupted. Ask again." });
    } catch (error) {
      update({ error: (error as Error).message });
    }
    if (mine === generation.current) (setBusy(false), refresh());
  }

  async function play(run: Run) {
    reset(run.id);
    history.replaceState(null, "", `?run=${run.id}`);
    const mine = generation.current;
    for (const turn of run.turns) if (mine === generation.current) await ask(turn.question);
  }

  function open(summary: Summary) {
    reset(summary.id, summary.id);
    const mine = generation.current;
    api.conversation(summary.id).then((found) => mine === generation.current && setShown(found.turns.map((turn) => ({ question: turn.question, phase: "verifying", turn }))), fail);
  }

  function remove(summary: Summary) {
    if (!confirm(`Delete "${summary.title}"? Its questions and answers are removed for good.`)) return;
    api.remove(summary.id).then(() => (active === summary.id && reset(), refresh()), fail);
  }

  function suggest(text: string) {
    const run = RUNS.find((item) => item.turns[0]?.question === text);
    if (!DEMO) ask(text);
    else if (run) play(run);
  }

  function send() {
    if (!draft.trim() || busy || DEMO) return;
    ask(draft.trim());
    setDraft("");
  }

  const listed = (DEMO
    ? RUNS.map((run): Item => ({ key: run.id, label: run.title, go: () => play(run) }))
    : summaries.map((summary): Item => ({ key: summary.id, label: summary.title, go: () => open(summary), remove: () => remove(summary) }))
  ).filter((item) => item.label.toLowerCase().includes((filter ?? "").toLowerCase()));
  const Icon = DEMO ? PlayCircle : MessageSquare;
  const initial = (me?.initials || me?.name || "?").charAt(0).toUpperCase();

  return (
    <div className="app">
      {DEMO && <header className="band">Demo mode · recorded runs from the deployed system</header>}
      <div className="layout">
        <button className="icon menu" aria-label="Sidebar" aria-expanded={menu} onClick={() => setMenu(!menu)}>
          <Menu size={20} />
        </button>
        <aside className={menu ? "sidebar open" : "sidebar"} aria-label="Sidebar" onKeyDown={(event) => event.key === "Escape" && setMenu(false)}>
          <h1>
            <img src={`${BRAND}juriscope-logo.svg`} alt="Juriscope" height={28} />
          </h1>
          <div className="row">
            <button className="primary" onClick={() => reset()}>
              <SquarePen size={16} aria-hidden /> New chat
            </button>
            <button className="icon round" aria-label="Search" aria-expanded={filter !== undefined} onClick={() => setFilter(filter === undefined ? "" : undefined)}>
              <Search size={16} />
            </button>
          </div>
          {filter !== undefined && <input className="search" aria-label="Search the list" autoFocus value={filter} onChange={(event) => setFilter(event.target.value)} />}
          <nav aria-label={DEMO ? "Recorded runs" : "Conversations"}>
            <h2>{DEMO ? "Recorded runs" : "Conversations"}</h2>
            <ul>
              {listed.map(({ key, label, go, remove }) => (
                  <li key={key} className={key === active ? "selected" : undefined}>
                    <button className="item" aria-current={key === active} onClick={go}>
                      <Icon size={16} aria-hidden /> <span>{label}</span>
                    </button>
                    {remove && (
                      <button className="icon" aria-label={`Delete ${label}`} onClick={remove}>
                        <Trash2 size={16} />
                      </button>
                    )}
                  </li>
                ))}
            </ul>
            {listed.length === 0 && <p className="status">{filter ? "Nothing matches the search." : DEMO ? "No recorded runs yet." : "No conversations yet."}</p>}
          </nav>
          <div className="me">
            <span className="avatar" aria-hidden>
              {initial}
            </span>
            <span>{me?.name || "Signed out"}</span>
            {!DEMO && (
              <a className="icon" href="/.auth/logout" aria-label="Sign out">
                <LogOut size={16} />
              </a>
            )}
          </div>
        </aside>
        <main inert={menu || undefined}>
          {failure && (
            <p className="status error" role="alert">
              {failure}
            </p>
          )}
          {shown.length === 0 ? (
            <div className="empty">
              <img src={`${BRAND}juriscope-logo.svg`} alt="Juriscope" height={48} />
              <h2>Cited answers on the Spanish Criminal Code, with the full article and the version in force.</h2>
              <div className="suggestions">
                {SUGGESTIONS.map((text) => (
                  <button key={text} className="suggestion" lang={text.startsWith("¿") ? "es" : undefined} disabled={busy || (DEMO && !RUNS.some((run) => run.turns[0]?.question === text))} onClick={() => suggest(text)}>
                    {text}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="thread" aria-label="Conversation">
              {shown.map((item, index) => (
                <div key={index}>
                  <div className="turn user">
                    <span className="avatar" aria-hidden>
                      {initial}
                    </span>
                    <p>{item.question}</p>
                  </div>
                  <section className="turn product" aria-label="Juriscope">
                    <p className="name">Juriscope</p>
                    {item.error ? (
                      <p className="status error" role="alert">
                        {item.error}
                      </p>
                    ) : item.turn ? (
                      <Outcome turn={item.turn} meta={meta} />
                    ) : (
                      <Progress shown={item} />
                    )}
                  </section>
                </div>
              ))}
              <div ref={end} />
            </div>
          )}
          <form className="composer" onSubmit={(event) => (event.preventDefault(), send())}>
            <textarea
              aria-label="Question"
              rows={1}
              value={draft}
              disabled={DEMO}
              placeholder={DEMO ? "Typing requires the deployed system: pick a recorded run" : "Ask about the Criminal Code. Do not paste client names or other identities."}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing && (event.preventDefault(), send())}
            />
            <button type="submit" className="send" aria-label="Send" disabled={DEMO || busy || !draft.trim()}>
              <ArrowUp size={18} />
            </button>
          </form>
        </main>
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
