import type { Route } from "./+types/home";
import { Welcome } from "../welcome/welcome";
import { UI_LEXICON } from "../utils/uiLexicon";

export function meta({}: Route.MetaArgs) {
  return [
    { title: UI_LEXICON.es.common.appTitle },
    {
      name: "description",
      content: UI_LEXICON.es.landing.eyebrow,
    },
  ];
}

export default function Home() {
  return <Welcome />;
}
