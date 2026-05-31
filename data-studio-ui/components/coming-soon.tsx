type Props = {
  title: string;
  blurb?: string;
};

export function ComingSoon({ title, blurb }: Props) {
  return (
    <section className="panel">
      <h1>{title}</h1>
      <p className="hint">{blurb ?? "This area is planned for a future PH-DB-11 workpackage."}</p>
    </section>
  );
}
