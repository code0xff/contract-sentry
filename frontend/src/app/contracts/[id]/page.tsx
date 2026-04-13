import { getContract } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ContractDetail({ params }: { params: { id: string } }) {
  const c = await getContract(params.id);
  return (
    <section>
      <h2>{c.name}</h2>
      <p>Language: {c.language}</p>
      <p>Created: {c.created_at}</p>
      <p>
        <a href={`/contracts/${c.id}/simulations`}>Simulations</a>
      </p>
    </section>
  );
}
