export type AppLanguage = "es" | "ca" | "en" | "fr" | "pt";

export type InfoSection = {
  title: string;
  body: string;
};

export type UiCopy = {
  common: {
    appTitle: string;
    languageSelectorAria: string;
    loadingResume: string;
    loadingPrepare: string;
    close: string;
    languageNames: Record<AppLanguage, string>;
    welcomeWords: Record<AppLanguage, string>;
  };
  languageEntry: {
    title: string;
    subtitle: string;
  };
  landing: {
    eyebrow: string;
    title: string;
    subtitle: string;
    intro: string;
    braceletLabel: string;
    braceletPlaceholder: string;
    moreInfoButton: string;
    ageCheckbox: string;
    participationCheckbox: string;
    dataCheckbox: string;
    cta: string;
    footer: string;
    errors: {
      braceletRequired: string;
      consentsRequired: string;
      loading: string;
    };
  };
  infoModal: {
    title: string;
    sections: InfoSection[];
  };
  instructions: {
    title: string;
    intro: string;
    body: string;
    odds: string;
    prizeTableLabel: string;
    cta: string;
  };
  comprehension: {
    eyebrow: string;
    title: string;
    options: [string, string, string];
    errorEmpty: string;
    errorWrong: string;
    cta: string;
  };
  game: {
    title: string;
    intro: string;
    visibleResultLabel: string;
    firstResultTemplate: string;
    continueCta: string;
    firstRollCta: string;
    rerollCta: string;
    loading: string;
    attemptsTemplate: string;
    errors: {
      noSession: string;
      loadRoll: string;
      loadReport: string;
    };
  };
  report: {
    title: string;
    body: string;
    errorSave: string;
  };
  prizeReveal: {
    eyebrow: string;
    title: string;
    helper: string;
    winnerResult: string;
    loserResult: string;
    optionLabel: string;
    footer: string;
  };
  treatment: {
    controlTitle: string;
    controlBody: string;
    socialMessageTemplate: string;
  };
  winner: {
    eyebrow: string;
    title: string;
    amountLabel: string;
    codeLabelTemplate: string;
    cta: string;
  };
  loser: {
    eyebrow: string;
    title: string;
    body: string;
    bodySecondary: string;
    bodyFooter: string;
    shareLabel: string;
    shareMessageTemplate: string;
  };
  paused: {
    eyebrow: string;
    title: string;
    body: string;
    bodySecondary: string;
    emailLabel: string;
    emailPlaceholder: string;
    cta: string;
    legalHint: string;
    success: string;
    errorEmail: string;
    errorDefault: string;
  };
  paymentPage: {
    eyebrow: string;
    title: string;
    intro: string;
    codeLabel: string;
    phoneLabel: string;
    phonePlaceholder: string;
    messageLabel: string;
    messagePlaceholder: string;
    donationHint: string;
    lookupLabel: string;
    submitLabel: string;
    success: string;
    invalidCode: string;
    alreadyUsed: string;
    lookupHelpTemplate: string;
    successEyebrow: string;
    successTitle: string;
    successBody: string;
    successSecondary: string;
    successFooter: string;
    successShareLabel: string;
    successShareMessageTemplate: string;
    errorDefault: string;
  };
  accessibility: {
    diceRollAria: string;
  };
  serverErrors: Record<string, string>;
};

type TranslationSeed = Omit<UiCopy, "serverErrors" | "common"> & {
  common: Omit<UiCopy["common"], "welcomeWords" | "languageNames">;
  errors: {
    braceletNotFound: string;
    accessInvalid: string;
    sessionNotFound: string;
    actionUnavailable: string;
    defaultMessage: string;
  };
};

export const SUPPORTED_LANGUAGES: AppLanguage[] = ["es", "ca", "en", "fr", "pt"];

const SHARED_LANGUAGE_NAMES: Record<AppLanguage, string> = {
  es: "Español",
  ca: "Català",
  en: "English",
  fr: "Français",
  pt: "Português",
};

const SHARED_WELCOME_WORDS: Record<AppLanguage, string> = {
  es: "Bienvenido",
  ca: "Benvingut",
  en: "Welcome",
  fr: "Bienvenue",
  pt: "Bem-vindo",
};

function withServerErrors(seed: TranslationSeed): UiCopy {
  return {
    ...seed,
    common: {
      ...seed.common,
      languageNames: SHARED_LANGUAGE_NAMES,
      welcomeWords: SHARED_WELCOME_WORDS,
    },
    serverErrors: {
      "Pulsera no encontrada": seed.errors.braceletNotFound,
      "Es necesario confirmar edad, participacion y tratamiento de datos":
        seed.errors.accessInvalid,
      "Secuencia de tiradas invalida": seed.errors.actionUnavailable,
      "No quedan mas tiradas permitidas": seed.errors.actionUnavailable,
      "Todavia no existe primera tirada": seed.errors.actionUnavailable,
      "No existe primera tirada": seed.errors.actionUnavailable,
      "Pantalla no valida": seed.errors.actionUnavailable,
      "La sesion ya tiene claim": seed.errors.actionUnavailable,
      "Sesion no encontrada": seed.errors.sessionNotFound,
      "El experimento esta temporalmente detenido": seed.errors.actionUnavailable,
      "Email no valido": seed.errors.defaultMessage,
      "Serie no encontrada": seed.errors.defaultMessage,
      "Codigo no elegible para cobro": seed.errors.defaultMessage,
      "Codigo de cobro ya utilizado": seed.errors.actionUnavailable,
    },
  };
}

const es = withServerErrors({
  common: {
    appTitle: "SONAR 2026",
    languageSelectorAria: "Seleccionar idioma",
    loadingResume: "Recuperando sesión",
    loadingPrepare: "Preparando experiencia",
    close: "Cerrar",
  },
  languageEntry: {
    title: "",
    subtitle: "Select your language",
  },
  landing: {
    eyebrow: "Participa, 60 seg, y sorteamos:",
    title:
      "2 entradas VIP para SONAR 2027\ny cientos de premios de hasta 60 euros",
    subtitle: "",
    intro: "",
    braceletLabel: "ID de pulsera",
    braceletPlaceholder: "Ej: 10000001",
    moreInfoButton: "Más información",
    ageCheckbox: "Tengo 18 años o más",
    participationCheckbox: "Acepto participar",
    dataCheckbox: "Acepto el tratamiento de datos",
    cta: "Comenzar",
    footer: "",
    errors: {
      braceletRequired: "Introduce el ID de tu pulsera",
      consentsRequired: "Marca las tres casillas para continuar",
      loading: "Entrando...",
    },
  },
  infoModal: {
    title: "Información",
    sections: [
      {
        title: "Qué es esta actividad",
        body:
          "Esta actividad forma parte de un estudio académico sobre toma de decisiones en contextos digitales y culturales. Se realiza en colaboración con un laboratorio de economía del comportamiento.",
      },
      {
        title: "Qué tendrás que hacer",
        body:
          "Introducirás el código de tu pulsera, verás una tirada privada, podrás hacer lanzamientos extra de comprobación y después indicar el número de tu primera tirada. El proceso dura alrededor de un minuto.",
      },
      {
        title: "Pago e incentivos",
        body:
          "La selección para pago es aleatoria. Si eres seleccionado, el importe depende del número que declares y se gestiona al finalizar la actividad.",
      },
      {
        title: "Privacidad y datos",
        body:
          "La pulsera se usa solo para evitar participaciones duplicadas. El análisis se realiza sin publicar identidades personales y los resultados se estudian de forma agregada.",
      },
      {
        title: "Participación voluntaria",
        body:
          "Participar es voluntario. Puedes dejar la actividad en cualquier momento antes de enviar tu respuesta final. Una vez anonimizados, los datos podrán usarse con fines científicos y de publicación académica.",
      },
      {
        title: "Contacto",
        body:
          "Si tienes dudas sobre el estudio o sobre el cobro, puedes consultarlo con el equipo del stand o escribir a lbl@uloyola.es.",
      },
    ],
  },
  instructions: {
    title: "Cómo funciona",
    intro:
      "Lanza un dado. Después te preguntaremos qué número salió en tu primera tirada.",
    body:
      "La primera tirada es la que cuenta. Según ese número, puedes ganar el premio que aparece en la tabla.",
    odds: "1 de cada 100 recibe el pago.",
    prizeTableLabel: "Tabla de premios",
    cta: "Continuar",
  },
  comprehension: {
    eyebrow: "Antes de seguir",
    title: "¿Qué número te vamos a pedir después?",
    options: ["Primera tirada", "Última tirada", "La más alta"],
    errorEmpty: "Selecciona una opción",
    errorWrong: "Recuerda: te pediremos el número de la primera tirada",
    cta: "Seguir",
  },
  game: {
    title: "Tirada",
    intro: "Pulsa el dado para ver otra tirada.",
    visibleResultLabel: "",
    firstResultTemplate: "Tu primera tirada: {value}",
    continueCta: "Continuar",
    firstRollCta: "Lanzar",
    rerollCta: "Probar el dado",
    loading: "Cargando...",
    attemptsTemplate: "Tiradas registradas: {count}/{max}",
    errors: {
      noSession: "No hay sesión activa",
      loadRoll: "No se pudo cargar la tirada",
      loadReport: "Acción no disponible",
    },
  },
  report: {
    title: "Tu primera tirada",
    body: "Indica el número que te salió al tirar el dado la primera vez.",
    errorSave: "No se pudo guardar la respuesta",
  },
  prizeReveal: {
    eyebrow: "Selección final",
    title: "Clica una",
    helper: "Elige una ficha para descubrir si has salido ganador.",
    winnerResult: "Esta era la ficha ganadora.",
    loserResult: "La ficha ganadora era otra.",
    optionLabel: "Ficha",
    footer: "",
  },
  treatment: {
    controlTitle: "Tu respuesta es anónima",
    controlBody: "Selecciona tu número",
    socialMessageTemplate:
      "{count} de cada {denominator} personas eligieron {target}.",
  },
  winner: {
    eyebrow: "Has sido seleccionado",
    title: "Premio confirmado",
    amountLabel: "Importe",
    codeLabelTemplate: "Código: {code}",
    cta: "Cobrar premio",
  },
  loser: {
    eyebrow: "Gracias por participar.",
    title: "Aún puedes ganar",
    body: "No has sido seleccionado para el premio en metálico.",
    bodySecondary:
      "Sigues participando en el sorteo de 2 entradas VIP. Invita a más personas que estén aquí hoy para aumentar tus posibilidades.",
    bodyFooter: "El resultado del estudio se publicará en cotec.es.",
    shareLabel: "Invitar por WhatsApp",
    shareMessageTemplate: "Participa en SONAR 2026: {link}",
  },
  paused: {
    eyebrow: "Gracias",
    title: "Todos los premios ya han sido repartidos",
    body: "La actividad está cerrada por ahora.",
    bodySecondary:
      "Si quieres recibir avisos sobre estudios similares, deja tu email.",
    emailLabel: "Email",
    emailPlaceholder: "nombre@correo.com",
    cta: "Avisarme",
    legalHint: "Solo usaremos tu email para futuros avisos del proyecto.",
    success: "Email guardado",
    errorEmail: "Introduce un email válido",
    errorDefault: "Error inesperado",
  },
  paymentPage: {
    eyebrow: "Cobro",
    title: "Introduce tu código y tu teléfono",
    intro: "",
    codeLabel: "Código",
    phoneLabel: "Teléfono",
    phonePlaceholder: "",
    messageLabel: "Mensaje (opcional)",
    messagePlaceholder: "",
    donationHint: "Puedes escribir ONG para donar",
    lookupLabel: "Validar código",
    submitLabel: "Enviar",
    success: "Solicitud enviada",
    invalidCode: "Código no válido",
    alreadyUsed: "Código ya usado",
    lookupHelpTemplate: "Código válido · {amount} EUR",
    successEyebrow: "Solicitud enviada",
    successTitle: "Aún puedes ganar",
    successBody: "Tu solicitud de cobro ha quedado registrada correctamente.",
    successSecondary:
      "Además, sigues participando en el sorteo de 2 entradas VIP. Invita a más amigos que estén hoy en el evento para aumentar tus posibilidades.",
    successFooter: "Los resultados del estudio se publicarán en cotec.es.",
    successShareLabel: "Invitar por WhatsApp",
    successShareMessageTemplate: "Participa en SONAR 2026: {link}",
    errorDefault: "Error al enviar",
  },
  accessibility: {
    diceRollAria: "Lanzar dado",
  },
  errors: {
    braceletNotFound: "Pulsera no encontrada",
    accessInvalid: "Acceso no válido",
    sessionNotFound: "Sesión no encontrada",
    actionUnavailable: "Acción no disponible",
    defaultMessage: "Error inesperado",
  },
});

const ca = withServerErrors({
  common: {
    appTitle: "SONAR 2026",
    languageSelectorAria: "Seleccionar idioma",
    loadingResume: "Recuperant sessió",
    loadingPrepare: "Preparant experiència",
    close: "Tancar",
  },
  languageEntry: {
    title: "",
    subtitle: "Select your language",
  },
  landing: {
    eyebrow: "Participa, 60 s, i sortegem:",
    title:
      "2 entrades VIP per a SONAR 2027\ni centenars de premis de fins a 60 euros",
    subtitle: "",
    intro: "",
    braceletLabel: "ID de polsera",
    braceletPlaceholder: "Ex: 10000001",
    moreInfoButton: "Més informació",
    ageCheckbox: "Tinc 18 anys o més",
    participationCheckbox: "Accepto participar",
    dataCheckbox: "Accepto el tractament de dades",
    cta: "Començar",
    footer: "",
    errors: {
      braceletRequired: "Introdueix l'ID de la polsera",
      consentsRequired: "Marca les tres caselles per continuar",
      loading: "Entrant...",
    },
  },
  infoModal: {
    title: "Informació",
    sections: [
      {
        title: "Què és aquesta activitat",
        body:
          "Aquesta activitat forma part d'un estudi acadèmic sobre presa de decisions en contextos digitals i culturals. Es fa en col·laboració amb un laboratori d'economia del comportament.",
      },
      {
        title: "Què hauràs de fer",
        body:
          "Introduiràs el codi de la polsera, veuràs una tirada privada, podràs fer llançaments extra de comprovació i després indicar el número de la teva primera tirada. El procés dura al voltant d'un minut.",
      },
      {
        title: "Pagament i incentius",
        body:
          "La selecció per al pagament és aleatòria. Si resultes seleccionat, l'import depèn del número que declaris i es gestiona al final de l'activitat.",
      },
      {
        title: "Privadesa i dades",
        body:
          "La polsera s'utilitza només per evitar participacions duplicades. L'anàlisi es fa sense publicar identitats personals i els resultats s'estudien de forma agregada.",
      },
      {
        title: "Participació voluntària",
        body:
          "Participar és voluntari. Pots deixar l'activitat en qualsevol moment abans d'enviar la teva resposta final. Un cop anonimitzades, les dades es podran fer servir amb finalitats científiques i de publicació acadèmica.",
      },
      {
        title: "Contacte",
        body:
          "Si tens dubtes sobre l'estudi o sobre el cobrament, pots consultar-ho amb l'equip de l'estand o escriure a lbl@uloyola.es.",
      },
    ],
  },
  instructions: {
    title: "Com funciona",
    intro:
      "Llança un dau. Després et preguntarem quin número va sortir a la teva primera tirada.",
    body:
      "La primera tirada és la que compta. Segons aquest número, pots guanyar el premi que apareix a la taula.",
    odds: "1 de cada 100 rep el pagament.",
    prizeTableLabel: "Taula de premis",
    cta: "Continuar",
  },
  comprehension: {
    eyebrow: "Abans de seguir",
    title: "Quin número et demanarem després?",
    options: ["Primera tirada", "Última tirada", "La més alta"],
    errorEmpty: "Selecciona una opció",
    errorWrong: "Recorda: et demanarem el número de la primera tirada",
    cta: "Seguir",
  },
  game: {
    title: "Tirada",
    intro: "Prem el dau per veure una altra tirada.",
    visibleResultLabel: "",
    firstResultTemplate: "La teva primera tirada: {value}",
    continueCta: "Continuar",
    firstRollCta: "Llançar",
    rerollCta: "Provar el dau",
    loading: "Carregant...",
    attemptsTemplate: "Tirades registrades: {count}/{max}",
    errors: {
      noSession: "No hi ha sessió activa",
      loadRoll: "No s'ha pogut carregar la tirada",
      loadReport: "Acció no disponible",
    },
  },
  report: {
    title: "La teva primera tirada",
    body: "Indica el número que et va sortir en tirar el dau la primera vegada.",
    errorSave: "No s'ha pogut guardar la resposta",
  },
  prizeReveal: {
    eyebrow: "Selecció final",
    title: "Tria'n una",
    helper: "Escull una fitxa per descobrir si has estat guanyador.",
    winnerResult: "Aquesta era la fitxa guanyadora.",
    loserResult: "La fitxa guanyadora era una altra.",
    optionLabel: "Fitxa",
    footer: "",
  },
  treatment: {
    controlTitle: "La teva resposta és anònima",
    controlBody: "Selecciona el teu número",
    socialMessageTemplate:
      "{count} de cada {denominator} persones van escollir {target}.",
  },
  winner: {
    eyebrow: "Has estat seleccionat",
    title: "Premi confirmat",
    amountLabel: "Import",
    codeLabelTemplate: "Codi: {code}",
    cta: "Cobrar premi",
  },
  loser: {
    eyebrow: "Gràcies per participar.",
    title: "Encara pots guanyar",
    body: "No has estat seleccionat per al premi en metàl·lic.",
    bodySecondary:
      "Continues participant en el sorteig de 2 entrades VIP. Convida més persones que siguin aquí avui per augmentar les teves possibilitats.",
    bodyFooter: "El resultat de l'estudi es publicarà a cotec.es.",
    shareLabel: "Convidar per WhatsApp",
    shareMessageTemplate: "Participa a SONAR 2026: {link}",
  },
  paused: {
    eyebrow: "Gràcies",
    title: "Tots els premis ja s'han repartit",
    body: "L'activitat està tancada per ara.",
    bodySecondary:
      "Si vols rebre avisos sobre estudis similars, deixa el teu correu.",
    emailLabel: "Correu",
    emailPlaceholder: "nom@correu.com",
    cta: "Avisa'm",
    legalHint: "Només farem servir el teu correu per a futurs avisos del projecte.",
    success: "Correu desat",
    errorEmail: "Introdueix un correu vàlid",
    errorDefault: "Error inesperat",
  },
  paymentPage: {
    eyebrow: "Cobrament",
    title: "Introdueix el teu codi i el teu telèfon",
    intro: "",
    codeLabel: "Codi",
    phoneLabel: "Telèfon",
    phonePlaceholder: "",
    messageLabel: "Missatge (opcional)",
    messagePlaceholder: "",
    donationHint: "Pots escriure ONG per donar",
    lookupLabel: "Validar codi",
    submitLabel: "Enviar",
    success: "Sol·licitud enviada",
    invalidCode: "Codi no vàlid",
    alreadyUsed: "Codi ja utilitzat",
    lookupHelpTemplate: "Codi vàlid · {amount} EUR",
    successEyebrow: "Sol·licitud enviada",
    successTitle: "Encara pots guanyar",
    successBody: "La teva sol·licitud de cobrament ha quedat registrada correctament.",
    successSecondary:
      "A més, continues participant en el sorteig de 2 entrades VIP. Convida més amics que siguin avui a l'esdeveniment per augmentar les teves possibilitats.",
    successFooter: "Els resultats de l'estudi es publicaran a cotec.es.",
    successShareLabel: "Convidar per WhatsApp",
    successShareMessageTemplate: "Participa a SONAR 2026: {link}",
    errorDefault: "Error en enviar",
  },
  accessibility: {
    diceRollAria: "Llançar dau",
  },
  errors: {
    braceletNotFound: "Polsera no trobada",
    accessInvalid: "Accés no vàlid",
    sessionNotFound: "Sessió no trobada",
    actionUnavailable: "Acció no disponible",
    defaultMessage: "Error inesperat",
  },
});

const en = withServerErrors({
  common: {
    appTitle: "SONAR 2026",
    languageSelectorAria: "Select language",
    loadingResume: "Restoring session",
    loadingPrepare: "Preparing experience",
    close: "Close",
  },
  languageEntry: {
    title: "",
    subtitle: "Select your language",
  },
  landing: {
    eyebrow: "Join in, 60 sec, and we raffle:",
    title:
      "2 VIP tickets for SONAR 2027\nand hundreds of prizes up to 60 euros",
    subtitle: "",
    intro: "",
    braceletLabel: "Bracelet ID",
    braceletPlaceholder: "Eg: 10000001",
    moreInfoButton: "More information",
    ageCheckbox: "I am 18 or older",
    participationCheckbox: "I agree to take part",
    dataCheckbox: "I agree to data processing",
    cta: "Start",
    footer: "",
    errors: {
      braceletRequired: "Enter your bracelet ID",
      consentsRequired: "Tick all three boxes to continue",
      loading: "Entering...",
    },
  },
  infoModal: {
    title: "Information",
    sections: [
      {
        title: "What this activity is",
        body:
          "This activity is part of an academic study on decision-making in digital and cultural settings. It is run in collaboration with a behavioural economics lab.",
      },
      {
        title: "What you will do",
        body:
          "You will enter your bracelet code, see a private roll, you may request extra checking rolls, and then report the number from your first roll. The process takes about one minute.",
      },
      {
        title: "Payment and incentives",
        body:
          "Selection for payment is random. If you are selected, the amount depends on the number you report and is handled after the activity ends.",
      },
      {
        title: "Privacy and data",
        body:
          "The bracelet is used only to prevent duplicate participation. Analysis is done without publishing personal identities and results are studied in aggregate form.",
      },
      {
        title: "Voluntary participation",
        body:
          "Participation is voluntary. You may leave at any time before submitting your final response. Once anonymised, the data may be used for scientific and academic publication purposes.",
      },
      {
        title: "Contact",
        body:
          "If you have questions about the study or payment, you can ask the team at the stand or write to lbl@uloyola.es.",
      },
    ],
  },
  instructions: {
    title: "How it works",
    intro: "Roll the die. Then we will ask which number came up on your first roll.",
    body:
      "The first roll is the one that counts. Based on that number, you may win the prize shown in the table.",
    odds: "1 in 100 receives payment.",
    prizeTableLabel: "Prize table",
    cta: "Continue",
  },
  comprehension: {
    eyebrow: "Before you continue",
    title: "Which number will we ask you for next?",
    options: ["First roll", "Last roll", "The highest one"],
    errorEmpty: "Select one option",
    errorWrong: "Remember: we will ask for the number from the first roll",
    cta: "Continue",
  },
  game: {
    title: "Roll",
    intro: "Tap the die to see another roll.",
    visibleResultLabel: "",
    firstResultTemplate: "Your first roll: {value}",
    continueCta: "Continue",
    firstRollCta: "Roll",
    rerollCta: "Try the die",
    loading: "Loading...",
    attemptsTemplate: "Rolls recorded: {count}/{max}",
    errors: {
      noSession: "No active session",
      loadRoll: "Could not load the roll",
      loadReport: "Action unavailable",
    },
  },
  report: {
    title: "Your first roll",
    body: "Enter the number that came up when you rolled the die the first time.",
    errorSave: "Could not save your response",
  },
  prizeReveal: {
    eyebrow: "Final selection",
    title: "Pick one",
    helper: "Choose one tile to discover whether you are a winner.",
    winnerResult: "This was the winning tile.",
    loserResult: "A different tile was the winning one.",
    optionLabel: "Tile",
    footer: "",
  },
  treatment: {
    controlTitle: "Your response is anonymous",
    controlBody: "Select your number",
    socialMessageTemplate:
      "{count} out of every {denominator} people chose {target}.",
  },
  winner: {
    eyebrow: "You were selected",
    title: "Prize confirmed",
    amountLabel: "Amount",
    codeLabelTemplate: "Code: {code}",
    cta: "Claim prize",
  },
  loser: {
    eyebrow: "Thanks for taking part.",
    title: "You can still win",
    body: "You were not selected for the cash prize.",
    bodySecondary:
      "You are still entered in the draw for 2 VIP tickets. Invite more people who are here today to improve your chances.",
    bodyFooter: "The study result will be published at cotec.es.",
    shareLabel: "Invite on WhatsApp",
    shareMessageTemplate: "Take part in SONAR 2026: {link}",
  },
  paused: {
    eyebrow: "Thank you",
    title: "All prizes have already been distributed",
    body: "This activity is closed for now.",
    bodySecondary:
      "If you want updates about similar studies, leave your email.",
    emailLabel: "Email",
    emailPlaceholder: "name@email.com",
    cta: "Notify me",
    legalHint: "We will only use your email for future project updates.",
    success: "Email saved",
    errorEmail: "Enter a valid email",
    errorDefault: "Unexpected error",
  },
  paymentPage: {
    eyebrow: "Payment",
    title: "Enter your code and your phone",
    intro: "",
    codeLabel: "Code",
    phoneLabel: "Phone",
    phonePlaceholder: "",
    messageLabel: "Message (optional)",
    messagePlaceholder: "",
    donationHint: "You can write ONG to donate",
    lookupLabel: "Validate code",
    submitLabel: "Send",
    success: "Request sent",
    invalidCode: "Invalid code",
    alreadyUsed: "Code already used",
    lookupHelpTemplate: "Valid code · {amount} EUR",
    successEyebrow: "Request sent",
    successTitle: "You can still win",
    successBody: "Your payment request has been recorded successfully.",
    successSecondary:
      "You are also still entered in the draw for 2 VIP tickets. Invite more friends who are at the event today to improve your chances.",
    successFooter: "The study results will be published at cotec.es.",
    successShareLabel: "Invite on WhatsApp",
    successShareMessageTemplate: "Take part in SONAR 2026: {link}",
    errorDefault: "Error sending request",
  },
  accessibility: {
    diceRollAria: "Roll die",
  },
  errors: {
    braceletNotFound: "Bracelet not found",
    accessInvalid: "Invalid access",
    sessionNotFound: "Session not found",
    actionUnavailable: "Action unavailable",
    defaultMessage: "Unexpected error",
  },
});

const fr = withServerErrors({
  common: {
    appTitle: "SONAR 2026",
    languageSelectorAria: "Choisir la langue",
    loadingResume: "Récupération de la session",
    loadingPrepare: "Préparation de l'expérience",
    close: "Fermer",
  },
  languageEntry: {
    title: "",
    subtitle: "Select your language",
  },
  landing: {
    eyebrow: "Participez, 60 sec, et nous tirons au sort :",
    title:
      "2 billets VIP pour SONAR 2027\net des centaines de prix jusqu'a 60 euros",
    subtitle: "",
    intro: "",
    braceletLabel: "ID du bracelet",
    braceletPlaceholder: "Ex : 10000001",
    moreInfoButton: "Plus d'information",
    ageCheckbox: "J'ai 18 ans ou plus",
    participationCheckbox: "J'accepte de participer",
    dataCheckbox: "J'accepte le traitement des données",
    cta: "Commencer",
    footer: "",
    errors: {
      braceletRequired: "Entrez l'ID de votre bracelet",
      consentsRequired: "Cochez les trois cases pour continuer",
      loading: "Entrée...",
    },
  },
  infoModal: {
    title: "Information",
    sections: [
      {
        title: "Ce qu'est cette activité",
        body:
          "Cette activité fait partie d'une étude académique sur la prise de décision dans des contextes numériques et culturels. Elle est menée en collaboration avec un laboratoire d'économie comportementale.",
      },
      {
        title: "Ce que vous ferez",
        body:
          "Vous saisirez le code de votre bracelet, verrez un lancer privé, pourrez demander des lancers supplémentaires de vérification, puis indiquerez le nombre de votre premier lancer. Le processus dure environ une minute.",
      },
      {
        title: "Paiement et incitations",
        body:
          "La sélection pour le paiement est aléatoire. Si vous êtes sélectionné, le montant dépend du nombre que vous déclarez et est traité à la fin de l'activité.",
      },
      {
        title: "Vie privée et données",
        body:
          "Le bracelet est utilisé uniquement pour éviter les participations en double. L'analyse est réalisée sans publier d'identités personnelles et les résultats sont étudiés de manière agrégée.",
      },
      {
        title: "Participation volontaire",
        body:
          "La participation est volontaire. Vous pouvez quitter à tout moment avant d'envoyer votre réponse finale. Une fois anonymisées, les données peuvent être utilisées à des fins scientifiques et de publication académique.",
      },
      {
        title: "Contact",
        body:
          "Si vous avez des questions sur l'étude ou sur le paiement, vous pouvez demander à l'équipe sur le stand ou écrire à lbl@uloyola.es.",
      },
    ],
  },
  instructions: {
    title: "Comment ça marche",
    intro:
      "Lancez le dé. Ensuite, nous vous demanderons quel nombre est sorti lors de votre premier lancer.",
    body:
      "Le premier lancer est celui qui compte. Selon ce nombre, vous pourrez gagner le prix affiché dans le tableau.",
    odds: "1 personne sur 100 reçoit le paiement.",
    prizeTableLabel: "Table des prix",
    cta: "Continuer",
  },
  comprehension: {
    eyebrow: "Avant de continuer",
    title: "Quel nombre allons-nous vous demander ensuite ?",
    options: ["Premier lancer", "Dernier lancer", "Le plus élevé"],
    errorEmpty: "Sélectionnez une option",
    errorWrong: "Rappelez-vous : nous vous demanderons le nombre du premier lancer",
    cta: "Continuer",
  },
  game: {
    title: "Lancer",
    intro: "Touchez le dé pour voir un autre lancer.",
    visibleResultLabel: "",
    firstResultTemplate: "Votre premier lancer : {value}",
    continueCta: "Continuer",
    firstRollCta: "Lancer",
    rerollCta: "Essayer le dé",
    loading: "Chargement...",
    attemptsTemplate: "Lancers enregistrés : {count}/{max}",
    errors: {
      noSession: "Aucune session active",
      loadRoll: "Impossible de charger le lancer",
      loadReport: "Action indisponible",
    },
  },
  report: {
    title: "Votre premier lancer",
    body: "Indiquez le nombre obtenu lorsque vous avez lancé le dé la première fois.",
    errorSave: "Impossible d'enregistrer la réponse",
  },
  prizeReveal: {
    eyebrow: "Sélection finale",
    title: "Choisissez-en une",
    helper: "Choisissez une case pour découvrir si vous avez gagné.",
    winnerResult: "C'était la case gagnante.",
    loserResult: "La case gagnante était une autre.",
    optionLabel: "Case",
    footer: "",
  },
  treatment: {
    controlTitle: "Votre réponse est anonyme",
    controlBody: "Sélectionnez votre nombre",
    socialMessageTemplate:
      "{count} personnes sur {denominator} ont choisi {target}.",
  },
  winner: {
    eyebrow: "Vous avez été sélectionné",
    title: "Prix confirmé",
    amountLabel: "Montant",
    codeLabelTemplate: "Code : {code}",
    cta: "Recevoir le prix",
  },
  loser: {
    eyebrow: "Merci pour votre participation.",
    title: "Vous pouvez encore gagner",
    body: "Vous n'avez pas été sélectionné pour le prix en espèces.",
    bodySecondary:
      "Vous participez toujours au tirage de 2 billets VIP. Invitez d'autres personnes présentes aujourd'hui pour augmenter vos chances.",
    bodyFooter: "Le résultat de l'étude sera publié sur cotec.es.",
    shareLabel: "Inviter sur WhatsApp",
    shareMessageTemplate: "Participez à SONAR 2026 : {link}",
  },
  paused: {
    eyebrow: "Merci",
    title: "Tous les prix ont déjà été distribués",
    body: "Cette activité est fermée pour le moment.",
    bodySecondary:
      "Si vous souhaitez recevoir des nouvelles d'études similaires, laissez votre email.",
    emailLabel: "Email",
    emailPlaceholder: "nom@email.com",
    cta: "M'avertir",
    legalHint: "Nous utiliserons votre email uniquement pour de futurs messages du projet.",
    success: "Email enregistré",
    errorEmail: "Entrez un email valide",
    errorDefault: "Erreur inattendue",
  },
  paymentPage: {
    eyebrow: "Paiement",
    title: "Entrez votre code et votre téléphone",
    intro: "",
    codeLabel: "Code",
    phoneLabel: "Téléphone",
    phonePlaceholder: "",
    messageLabel: "Message (optionnel)",
    messagePlaceholder: "",
    donationHint: "Vous pouvez écrire ONG pour faire un don",
    lookupLabel: "Valider le code",
    submitLabel: "Envoyer",
    success: "Demande envoyée",
    invalidCode: "Code invalide",
    alreadyUsed: "Code déjà utilisé",
    lookupHelpTemplate: "Code valide · {amount} EUR",
    successEyebrow: "Demande envoyée",
    successTitle: "Vous pouvez encore gagner",
    successBody: "Votre demande de paiement a bien été enregistrée.",
    successSecondary:
      "Vous participez aussi toujours au tirage de 2 billets VIP. Invitez d'autres amis présents à l'événement aujourd'hui pour augmenter vos chances.",
    successFooter: "Les résultats de l'étude seront publiés sur cotec.es.",
    successShareLabel: "Inviter sur WhatsApp",
    successShareMessageTemplate: "Participez à SONAR 2026 : {link}",
    errorDefault: "Erreur lors de l'envoi",
  },
  accessibility: {
    diceRollAria: "Lancer le dé",
  },
  errors: {
    braceletNotFound: "Bracelet introuvable",
    accessInvalid: "Accès invalide",
    sessionNotFound: "Session introuvable",
    actionUnavailable: "Action indisponible",
    defaultMessage: "Erreur inattendue",
  },
});

const pt = withServerErrors({
  common: {
    appTitle: "SONAR 2026",
    languageSelectorAria: "Selecionar idioma",
    loadingResume: "A recuperar sessão",
    loadingPrepare: "A preparar experiência",
    close: "Fechar",
  },
  languageEntry: {
    title: "",
    subtitle: "Select your language",
  },
  landing: {
    eyebrow: "Participa, 60 seg, e sorteamos:",
    title:
      "2 entradas VIP para o SONAR 2027\ne centenas de premios ate 60 euros",
    subtitle: "",
    intro: "",
    braceletLabel: "ID da pulseira",
    braceletPlaceholder: "Ex: 10000001",
    moreInfoButton: "Mais informação",
    ageCheckbox: "Tenho 18 anos ou mais",
    participationCheckbox: "Aceito participar",
    dataCheckbox: "Aceito o tratamento de dados",
    cta: "Começar",
    footer: "",
    errors: {
      braceletRequired: "Introduz o ID da tua pulseira",
      consentsRequired: "Marca as três caixas para continuar",
      loading: "A entrar...",
    },
  },
  infoModal: {
    title: "Informação",
    sections: [
      {
        title: "O que é esta atividade",
        body:
          "Esta atividade faz parte de um estudo académico sobre tomada de decisões em contextos digitais e culturais. É realizada em colaboração com um laboratório de economia comportamental.",
      },
      {
        title: "O que vais fazer",
        body:
          "Vais introduzir o código da pulseira, ver uma tirada privada, poder pedir lançamentos extra de verificação e depois indicar o número da tua primeira tirada. O processo dura cerca de um minuto.",
      },
      {
        title: "Pagamento e incentivos",
        body:
          "A seleção para pagamento é aleatória. Se fores selecionado, o valor depende do número que declarares e é tratado no final da atividade.",
      },
      {
        title: "Privacidade e dados",
        body:
          "A pulseira é usada apenas para evitar participações duplicadas. A análise é feita sem publicar identidades pessoais e os resultados são estudados de forma agregada.",
      },
      {
        title: "Participação voluntária",
        body:
          "Participar é voluntário. Podes sair a qualquer momento antes de enviares a tua resposta final. Depois de anonimizados, os dados podem ser usados para fins científicos e de publicação académica.",
      },
      {
        title: "Contacto",
        body:
          "Se tiveres dúvidas sobre o estudo ou sobre o pagamento, podes falar com a equipa no stand ou escrever para lbl@uloyola.es.",
      },
    ],
  },
  instructions: {
    title: "Como funciona",
    intro:
      "Lança o dado. Depois vamos perguntar que número saiu na tua primeira tirada.",
    body:
      "A primeira tirada é a que conta. Consoante esse número, poderás ganhar o prémio que aparece na tabela.",
    odds: "1 em cada 100 recebe o pagamento.",
    prizeTableLabel: "Tabela de prémios",
    cta: "Continuar",
  },
  comprehension: {
    eyebrow: "Antes de continuar",
    title: "Que número te vamos pedir depois?",
    options: ["Primeira tirada", "Última tirada", "A mais alta"],
    errorEmpty: "Seleciona uma opção",
    errorWrong: "Lembra-te: vamos pedir o número da primeira tirada",
    cta: "Seguir",
  },
  game: {
    title: "Tirada",
    intro: "Toca no dado para ver outra tirada.",
    visibleResultLabel: "",
    firstResultTemplate: "A tua primeira tirada: {value}",
    continueCta: "Continuar",
    firstRollCta: "Lançar",
    rerollCta: "Provar o dado",
    loading: "A carregar...",
    attemptsTemplate: "Tiradas registadas: {count}/{max}",
    errors: {
      noSession: "Não há sessão ativa",
      loadRoll: "Não foi possível carregar a tirada",
      loadReport: "Ação indisponível",
    },
  },
  report: {
    title: "A tua primeira tirada",
    body: "Indica o número que te saiu ao lançar o dado na primeira vez.",
    errorSave: "Não foi possível guardar a resposta",
  },
  prizeReveal: {
    eyebrow: "Seleção final",
    title: "Escolhe uma",
    helper: "Escolhe uma ficha para descobrir se saíste vencedor.",
    winnerResult: "Esta era a premiada.",
    loserResult: "A premiada era outra.",
    optionLabel: "Ficha",
    footer: "",
  },
  treatment: {
    controlTitle: "A tua resposta é anónima",
    controlBody: "Seleciona o teu número",
    socialMessageTemplate:
      "{count} de cada {denominator} pessoas escolheram {target}.",
  },
  winner: {
    eyebrow: "Foste selecionado",
    title: "Prémio confirmado",
    amountLabel: "Valor",
    codeLabelTemplate: "Código: {code}",
    cta: "Receber prémio",
  },
  loser: {
    eyebrow: "Obrigado por participar.",
    title: "Ainda podes ganhar",
    body: "Não foste selecionado para o prémio em dinheiro.",
    bodySecondary:
      "Continuas a participar no sorteio de 2 entradas VIP. Convida mais pessoas que estejam aqui hoje para aumentar as tuas possibilidades.",
    bodyFooter: "O resultado do estudo será publicado em cotec.es.",
    shareLabel: "Convidar por WhatsApp",
    shareMessageTemplate: "Participa no SONAR 2026: {link}",
  },
  paused: {
    eyebrow: "Obrigado",
    title: "Todos os prémios já foram distribuídos",
    body: "A atividade está fechada por agora.",
    bodySecondary:
      "Se quiseres receber avisos sobre estudos semelhantes, deixa o teu email.",
    emailLabel: "Email",
    emailPlaceholder: "nome@email.com",
    cta: "Avisar-me",
    legalHint: "Só vamos usar o teu email para futuros avisos do projeto.",
    success: "Email guardado",
    errorEmail: "Introduz um email válido",
    errorDefault: "Erro inesperado",
  },
  paymentPage: {
    eyebrow: "Cobrança",
    title: "Introduz o teu código e o teu telefone",
    intro: "",
    codeLabel: "Código",
    phoneLabel: "Telefone",
    phonePlaceholder: "",
    messageLabel: "Mensagem (opcional)",
    messagePlaceholder: "",
    donationHint: "Podes escrever ONG para doar",
    lookupLabel: "Validar código",
    submitLabel: "Enviar",
    success: "Pedido enviado",
    invalidCode: "Código inválido",
    alreadyUsed: "Código já usado",
    lookupHelpTemplate: "Código válido · {amount} EUR",
    successEyebrow: "Pedido enviado",
    successTitle: "Ainda podes ganhar",
    successBody: "O teu pedido de cobrança ficou registado corretamente.",
    successSecondary:
      "Além disso, continuas a participar no sorteio de 2 entradas VIP. Convida mais amigos que estejam hoje no evento para aumentar as tuas possibilidades.",
    successFooter: "Os resultados do estudo serão publicados em cotec.es.",
    successShareLabel: "Convidar por WhatsApp",
    successShareMessageTemplate: "Participa no SONAR 2026: {link}",
    errorDefault: "Erro ao enviar",
  },
  accessibility: {
    diceRollAria: "Lançar dado",
  },
  errors: {
    braceletNotFound: "Pulseira não encontrada",
    accessInvalid: "Acesso inválido",
    sessionNotFound: "Sessão não encontrada",
    actionUnavailable: "Ação indisponível",
    defaultMessage: "Erro inesperado",
  },
});

export const UI_LEXICON: Record<AppLanguage, UiCopy> = {
  es,
  ca,
  en,
  fr,
  pt,
};

function collectLexiconPaths(value: unknown, prefix = ""): string[] {
  if (Array.isArray(value)) {
    return value.flatMap((entry, index) =>
      collectLexiconPaths(entry, `${prefix}[${index}]`),
    );
  }
  if (value && typeof value === "object") {
    return Object.entries(value).flatMap(([key, nested]) =>
      collectLexiconPaths(nested, prefix ? `${prefix}.${key}` : key),
    );
  }
  return prefix ? [prefix] : [];
}

export function validateLexiconCoverage() {
  const basePaths = new Set(collectLexiconPaths(UI_LEXICON.es));
  const missingByLanguage: Record<string, string[]> = {};

  for (const language of SUPPORTED_LANGUAGES) {
    const currentPaths = new Set(collectLexiconPaths(UI_LEXICON[language]));
    const missing = Array.from(basePaths).filter((path) => !currentPaths.has(path));
    if (missing.length > 0) {
      missingByLanguage[language] = missing;
    }
  }

  return missingByLanguage;
}

const missingLexiconKeys = validateLexiconCoverage();
if (Object.keys(missingLexiconKeys).length > 0) {
  throw new Error(
    `Missing UI lexicon keys: ${JSON.stringify(missingLexiconKeys)}`,
  );
}

export function formatCopy(
  template: string,
  values: Record<string, string | number | null | undefined>,
) {
  return template.replace(/\{(\w+)\}/g, (_, key: string) => {
    const value = values[key];
    return value === undefined || value === null ? "" : String(value);
  });
}

export function translateServerError(message: string, copy: UiCopy) {
  return copy.serverErrors[message] ?? message;
}

