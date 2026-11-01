export type Version = { norm: string; published: string; in_force: string; text: string; note: string | null };
export type Reference = { block_id: string; title: string; url: string };
export type Citation = Reference & { version: Version; current: Version | null; repealed: string | null; see_also: Reference[] };
export type Answer = { text: string; citations: Citation[]; claims: number; dropped_claims: number; language: string; facts_date: string | null };
export type Refusal = { reason: "out_of_scope" | "no_evidence" | "content_filter"; scope: string | null };
export type Turn = { id: string; question: string; asked: string; outcome: Answer | Refusal };
export type Summary = { id: string; title: string; updated: string };
export type Conversation = Summary & { turns: Turn[] };
export type Phase = { step: "analysing" | "searching" | "reading" | "drafting" | "verifying"; articles: number | null };
export type Meta = { updated: string; chat_model: string; embedding_model: string; notice: string };
export type Me = { name: string; initials: string };
export type Event =
  | { event: "phase"; data: Phase }
  | { event: "answer" | "refusal"; data: { conversation_id: string; turn: Turn } }
  | { event: "error"; data: { detail: string } };
export type Run = { id: string; title: string; recorded: string; meta: Meta; turns: { question: string; events: (Event & { at: number })[] }[] };

export const DEMO = import.meta.env.VITE_DEMO_MODE === "true";
const recordings = DEMO ? import.meta.glob<Run>("../fixtures/*.json", { eager: true, import: "default" }) : {};
export const RUNS = Object.values(recordings);
export const answered = (outcome: Answer | Refusal): outcome is Answer => "text" in outcome;

async function checked(path: string, init?: RequestInit): Promise<Response> {
  const response = await fetch(path, init);
  if (response.ok) return response;
  const body = await response.json().catch(() => ({}));
  throw new Error(typeof body.detail === "string" ? body.detail : `The request failed with status ${response.status}.`);
}

const json = async <T>(path: string, init?: RequestInit): Promise<T> => (await checked(path, init)).json();
const post = (body: unknown): RequestInit => ({ method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });

async function* parse(response: Response): AsyncGenerator<Event> {
  const reader = response.body!.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (let chunk = await reader.read(); !chunk.done; chunk = await reader.read()) {
    const blocks = (buffer + chunk.value.replace(/\r/g, "")).split("\n\n");
    buffer = blocks.pop() ?? "";
    for (const lines of blocks.map((block) => block.split("\n"))) {
      const event = lines.find((line) => line.startsWith("event:"))?.slice(6).trim();
      const data = lines.filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trim());
      if (event && data.length) yield { event, data: JSON.parse(data.join("\n")) } as Event;
    }
  }
}

async function* replay(question: string): AsyncGenerator<Event> {
  const turn = RUNS.flatMap((run) => run.turns).find((item) => item.question === question);
  if (!turn) throw new Error("Typing requires the deployed system. Pick a recorded run.");
  let elapsed = 0;
  for (const { at, ...event } of turn.events) {
    await new Promise((done) => setTimeout(done, at - elapsed));
    elapsed = at;
    yield event as Event;
  }
}

export const api = {
  me: () => (DEMO ? Promise.resolve({ name: "Demo visitor", initials: "D" }) : json<Me>("/api/me")),
  meta: () => (DEMO ? Promise.resolve(RUNS[0]?.meta) : json<Meta>("/api/meta")),
  conversations: () => json<Summary[]>("/api/conversations"),
  conversation: (id: string) => json<Conversation>(`/api/conversations/${id}`),
  remove: (id: string) => checked(`/api/conversations/${id}`, { method: "DELETE" }),
  feedback: (turn_id: string, value: "up" | "down" | "copy") => (DEMO ? Promise.resolve() : checked("/api/feedback", post({ turn_id, value })).then(() => undefined)),
  ask: async function* (id: string | undefined, question: string): AsyncGenerator<Event> {
    yield* DEMO ? replay(question) : parse(await checked(`/api/conversations/${id ?? "new"}/messages`, post({ question })));
  },
};
