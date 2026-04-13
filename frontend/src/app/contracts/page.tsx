import { listContracts } from "@/lib/api";
import type { Contract } from "@/types";

export const dynamic = "force-dynamic";

export default async function ContractListPage() {
  let contracts: Contract[] = [];
  try {
    contracts = await listContracts();
  } catch (e) {
    return <p>API unreachable: {(e as Error).message}</p>;
  }
  return (
    <section>
      <h2>Contracts</h2>
      {contracts.length === 0 && <p>No contracts uploaded yet.</p>}
      <ul>
        {contracts.map((c) => (
          <li key={c.id}>
            <a href={`/contracts/${c.id}`}>{c.name}</a> — {c.language}
          </li>
        ))}
      </ul>
    </section>
  );
}
