import type { Route } from "./+types/home";
import { Welcome } from "../welcome/welcome";
import { UI_LEXICON } from "../utils/uiLexicon";

export function meta({}: Route.MetaArgs) {
  const title = UI_LEXICON.es.common.appTitle;
  const description =
    "60 segundos. Puedes entrar en el sorteo de 2 entradas VIP para Sónar 2027 y optar a premios en dinero de hasta 60 €.";
  return [
    { title },
    {
      name: "description",
      content: description,
    },
    { property: "og:title", content: title },
    { property: "og:description", content: description },
    { property: "og:type", content: "website" },
    { name: "twitter:card", content: "summary" },
    { name: "twitter:title", content: title },
    { name: "twitter:description", content: description },
  ];
}

export default function Home() {
  return <Welcome />;
}
