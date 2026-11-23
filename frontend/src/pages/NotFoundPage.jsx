import { ButtonLink, PageHeading } from "../components/ui";

export default function NotFoundPage() {
  return (
    <PageHeading
      eyebrow="Erro 404"
      title="Página não encontrada."
      description="O endereço pode estar errado ou a página não existe mais."
      action={<ButtonLink to="/viagens">Voltar para minhas viagens</ButtonLink>}
    />
  );
}
