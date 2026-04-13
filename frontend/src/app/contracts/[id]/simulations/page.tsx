export default function SimulationsPage({ params }: { params: { id: string } }) {
  return (
    <section>
      <h2>Simulations for {params.id}</h2>
      <p>Trigger a simulation from the job detail page; results appear here once available.</p>
    </section>
  );
}
