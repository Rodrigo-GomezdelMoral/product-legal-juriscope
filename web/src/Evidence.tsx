import { Fragment } from "react";
import { DEMO } from "./api";

type Row = [string, string, number, string, boolean | null];
type Recorded = {
  recorded: string;
  gate: { title: string; source: string; run: string; rows: Row[]; footer: string };
  responses: { request: string; status: string; body: object }[];
  untested_live: string;
};

const found = DEMO ? import.meta.glob<Recorded>("../fixtures/evidence/*.json", { eager: true, import: "default" }) : {};
export const EVIDENCE = Object.values(found)[0];

export function Evidence({ evidence }: { evidence: Recorded }) {
  const { gate } = evidence;
  return (
    <section className="turn product evidence" aria-label="Recorded evidence">
      <p className="name">Recorded evidence · {evidence.recorded}</p>
      <div className="card">
        <h3>
          {gate.title} <small>REQ-05</small>
        </h3>
        <p className="label">{gate.source}</p>
        <p className="label">{gate.run}</p>
        <table>
          <thead>
            <tr>
              {["Metric", "Value", "Cases", "Threshold", "Pass"].map((name) => (
                <th key={name} scope="col">
                  {name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {gate.rows.map(([metric, value, cases, threshold, pass]) => (
              <tr key={metric}>
                <td>{metric}</td>
                <td>{value}</td>
                <td>{cases}</td>
                <td>{threshold}</td>
                <td>{pass === null ? "" : pass ? "✓" : "✗"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="notice">{gate.footer}</p>
      </div>
      <div className="card">
        <h3>
          Sign-in boundary on staging <small>REQ-07</small>
        </h3>
        {evidence.responses.map((item) => (
          <Fragment key={item.request}>
            <p className="label">
              {item.request}: {item.status}
            </p>
            <pre>{JSON.stringify(item.body, null, 1)}</pre>
          </Fragment>
        ))}
        <p className="notice">{evidence.untested_live}</p>
      </div>
    </section>
  );
}
