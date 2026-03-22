export type AppLanguage = "es" | "ca" | "en" | "fr" | "pt" | "it";

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
    initialIntro: string;
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
  bonusDraw: {
    title: string;
    intro: string;
    prompt: string;
    baseTicket: string;
    predictionTicket: string;
    inviteTicket: string;
    achievedLabel: string;
    predictionAchieved: string;
    selectedTemplate: string;
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
    donateLabel: string;
    consentLabel: string;
    consentInfoLabel: string;
    privacyModalTitle: string;
    privacySections: InfoSection[];
    success: string;
    invalidCode: string;
    alreadyUsed: string;
    lookupHelpTemplate: string;
    phoneRequired: string;
    consentRequired: string;
    successEyebrow: string;
    successTitle: string;
    successBody: string;
    successDonationBody: string;
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

export const SUPPORTED_LANGUAGES: AppLanguage[] = ["es", "ca", "en", "fr", "pt", "it"];

const SHARED_LANGUAGE_NAMES: Record<AppLanguage, string> = {
  es: "Español",
  ca: "Català",
  en: "English",
  fr: "Français",
  pt: "Português",
  it: "Italiano",
};

const SHARED_WELCOME_WORDS: Record<AppLanguage, string> = {
  es: "Bienvenido",
  ca: "Benvingut",
  en: "Welcome",
  fr: "Bienvenue",
  pt: "Bem-vindo",
  it: "Benvenuto",
};

const PAYMENT_PRIVACY_SECTIONS_ES: InfoSection[] = [
  {
    title: "Finalidad de este tratamiento",
    body:
      "Los datos que introduzcas en esta pantalla se utilizarán únicamente para gestionar el pago de tu premio por Bizum o, si lo prefieres, para tramitar la renuncia al cobro y registrar la donación equivalente a una ONG. Este tratamiento no se usa para tomar decisiones experimentales ni para analizar tu comportamiento dentro del estudio.",
  },
  {
    title: "Qué información se guarda",
    body:
      "Se registrarán el código de cobro, el teléfono facilitado para el Bizum o para la gestión administrativa asociada, el idioma de la solicitud, si has pedido el pago o la donación y la información mínima necesaria para poder justificar internamente la operación. No se solicitarán aquí más datos personales de los necesarios para completar la gestión económica.",
  },
  {
    title: "Separación respecto al experimento",
    body:
      "La información de cobro se almacenará en un sistema separado del experimento y en una base de datos distinta de la empleada para las respuestas experimentales. El equipo de análisis no necesita tu teléfono para estudiar el comportamiento observado en la tarea, y el procedimiento está diseñado para reducir al mínimo el cruce entre la información experimental y la información administrativa del pago.",
  },
  {
    title: "Conservación, acceso y trazabilidad",
    body:
      "Estos datos se conservarán durante el tiempo necesario para gestionar el pago o la donación, resolver incidencias, atender comprobaciones internas y cumplir las obligaciones legales, fiscales, contables y de auditoría que correspondan. Después se eliminarán o se mantendrán bloqueados solo durante los plazos exigidos por la normativa aplicable. El acceso quedará restringido al personal autorizado para la gestión administrativa del incentivo.",
  },
  {
    title: "Participación y derechos",
    body:
      "Solicitar el cobro o la donación es una acción voluntaria posterior al experimento. Si decides no continuar en esta pantalla, tu participación experimental ya habrá quedado registrada igualmente. Si tienes dudas sobre este tratamiento administrativo o sobre la gestión del pago, puedes consultarlo con el equipo presente en el stand antes de enviar la solicitud.",
  },
];

const PAYMENT_PRIVACY_SECTIONS_CA: InfoSection[] = [
  {
    title: "Finalitat d'aquest tractament",
    body:
      "Les dades que introdueixis en aquesta pantalla s'utilitzaran únicament per gestionar el pagament del teu premi per Bizum o, si ho prefereixes, per tramitar la renúncia al cobrament i registrar la donació equivalent a una ONG. Aquest tractament no s'utilitza per prendre decisions experimentals ni per analitzar el teu comportament dins de l'estudi.",
  },
  {
    title: "Quina informació es guarda",
    body:
      "Es registraran el codi de cobrament, el telèfon facilitat per al Bizum o per a la gestió administrativa associada, l'idioma de la sol·licitud, si has demanat el pagament o la donació i la informació mínima necessària per poder justificar internament l'operació. Aquí no se't demanaran més dades personals de les estrictament necessàries per completar la gestió econòmica.",
  },
  {
    title: "Separació respecte de l'experiment",
    body:
      "La informació de cobrament s'emmagatzemarà en un sistema separat de l'experiment i en una base de dades diferent de la utilitzada per a les respostes experimentals. L'equip d'anàlisi no necessita el teu telèfon per estudiar el comportament observat a la tasca, i el procediment està dissenyat per reduir al mínim l'encreuament entre la informació experimental i la informació administrativa del pagament.",
  },
  {
    title: "Conservació, accés i traçabilitat",
    body:
      "Aquestes dades es conservaran durant el temps necessari per gestionar el pagament o la donació, resoldre incidències, atendre comprovacions internes i complir les obligacions legals, fiscals, comptables i d'auditoria que corresponguin. Després s'eliminaran o es mantindran bloquejades només durant els terminis exigits per la normativa aplicable. L'accés quedarà restringit al personal autoritzat per a la gestió administrativa de l'incentiu.",
  },
  {
    title: "Participació i drets",
    body:
      "Sol·licitar el cobrament o la donació és una acció voluntària posterior a l'experiment. Si decideixes no continuar en aquesta pantalla, la teva participació experimental ja haurà quedat registrada igualment. Si tens dubtes sobre aquest tractament administratiu o sobre la gestió del pagament, pots consultar-ho amb l'equip present a l'estand abans d'enviar la sol·licitud.",
  },
];

const PAYMENT_PRIVACY_SECTIONS_EN: InfoSection[] = [
  {
    title: "Purpose of this processing",
    body:
      "The information entered on this screen will be used only to manage payment of your prize by Bizum or, if you prefer, to process your renunciation of payment and register the equivalent donation to an NGO. This processing is not used to make experimental decisions or to analyse your behaviour within the study.",
  },
  {
    title: "What information is stored",
    body:
      "We will record the payout code, the phone number provided for Bizum or the related administrative process, the language of the request, whether you asked for payment or donation, and the minimum information required to justify the transaction internally. No additional personal data beyond what is strictly necessary for the financial administration will be requested here.",
  },
  {
    title: "Separation from the experiment",
    body:
      "Payment information will be stored in a system that is separate from the experiment and in a database different from the one used for experimental responses. The analysis team does not need your phone number to study behaviour in the task, and the procedure is designed to minimise any link between experimental data and the administrative information used for payment.",
  },
  {
    title: "Retention, access and traceability",
    body:
      "These data will be kept for as long as needed to manage the payment or donation, resolve incidents, answer internal checks, and comply with the relevant legal, tax, accounting and audit obligations. Afterwards they will be deleted or kept blocked only for the retention periods required by applicable law. Access will be limited to authorised staff responsible for the administrative management of the incentive.",
  },
  {
    title: "Participation and rights",
    body:
      "Requesting payment or donation is a voluntary step that takes place after the experiment. If you decide not to continue on this screen, your experimental participation will already have been recorded. If you have questions about this administrative processing or about how the payment is managed, you can ask the team at the stand before submitting the request.",
  },
];

const PAYMENT_PRIVACY_SECTIONS_FR: InfoSection[] = [
  {
    title: "Finalité de ce traitement",
    body:
      "Les données saisies sur cet écran seront utilisées uniquement pour gérer le paiement de votre prix par Bizum ou, si vous le préférez, pour traiter votre renoncement au paiement et enregistrer le don équivalent à une ONG. Ce traitement n'est pas utilisé pour prendre des décisions expérimentales ni pour analyser votre comportement dans l'étude.",
  },
  {
    title: "Quelles informations sont conservées",
    body:
      "Seront enregistrés le code de paiement, le numéro de téléphone fourni pour le Bizum ou pour la gestion administrative associée, la langue de la demande, le fait que vous demandiez le paiement ou le don, ainsi que les informations minimales nécessaires pour justifier l'opération en interne. Aucune donnée personnelle supplémentaire au-delà de ce qui est strictement nécessaire à la gestion financière ne sera demandée ici.",
  },
  {
    title: "Séparation par rapport à l'expérience",
    body:
      "Les informations de paiement seront stockées dans un système séparé de l'expérience et dans une base de données différente de celle utilisée pour les réponses expérimentales. L'équipe d'analyse n'a pas besoin de votre numéro de téléphone pour étudier le comportement observé dans la tâche, et la procédure est conçue pour réduire au minimum le croisement entre les données expérimentales et les informations administratives de paiement.",
  },
  {
    title: "Conservation, accès et traçabilité",
    body:
      "Ces données seront conservées pendant le temps nécessaire pour gérer le paiement ou le don, résoudre les incidents, répondre aux vérifications internes et respecter les obligations légales, fiscales, comptables et d'audit applicables. Elles seront ensuite supprimées ou conservées sous forme bloquée uniquement pendant les délais exigés par la réglementation applicable. L'accès sera limité au personnel autorisé chargé de la gestion administrative de l'incitation.",
  },
  {
    title: "Participation et droits",
    body:
      "Demander le paiement ou le don est une démarche volontaire postérieure à l'expérience. Si vous décidez de ne pas continuer sur cet écran, votre participation expérimentale aura déjà été enregistrée. Si vous avez des questions sur ce traitement administratif ou sur la gestion du paiement, vous pouvez les poser à l'équipe présente sur le stand avant d'envoyer la demande.",
  },
];

const PAYMENT_PRIVACY_SECTIONS_PT: InfoSection[] = [
  {
    title: "Finalidade deste tratamento",
    body:
      "Os dados introduzidos neste ecrã serão usados apenas para gerir o pagamento do teu prémio por Bizum ou, se preferires, para tratar a renúncia ao recebimento e registar a doação equivalente a uma ONG. Este tratamento não é usado para tomar decisões experimentais nem para analisar o teu comportamento dentro do estudo.",
  },
  {
    title: "Que informação é guardada",
    body:
      "Serão registados o código de pagamento, o telefone fornecido para o Bizum ou para a gestão administrativa associada, o idioma do pedido, se pediste o pagamento ou a doação e a informação mínima necessária para justificar internamente a operação. Aqui não serão pedidos mais dados pessoais do que os estritamente necessários para concluir a gestão financeira.",
  },
  {
    title: "Separação em relação ao experimento",
    body:
      "A informação de pagamento será guardada num sistema separado do experimento e numa base de dados diferente da usada para as respostas experimentais. A equipa de análise não precisa do teu número de telefone para estudar o comportamento observado na tarefa, e o procedimento foi desenhado para reduzir ao mínimo a ligação entre os dados experimentais e a informação administrativa do pagamento.",
  },
  {
    title: "Conservação, acesso e rastreabilidade",
    body:
      "Estes dados serão conservados durante o tempo necessário para gerir o pagamento ou a doação, resolver incidências, responder a verificações internas e cumprir as obrigações legais, fiscais, contabilísticas e de auditoria aplicáveis. Depois serão eliminados ou mantidos bloqueados apenas durante os prazos exigidos pela legislação aplicável. O acesso ficará limitado ao pessoal autorizado responsável pela gestão administrativa do incentivo.",
  },
  {
    title: "Participação e direitos",
    body:
      "Solicitar o pagamento ou a doação é um passo voluntário posterior ao experimento. Se decidires não continuar neste ecrã, a tua participação experimental já terá sido registada na mesma. Se tiveres dúvidas sobre este tratamento administrativo ou sobre a gestão do pagamento, podes falar com a equipa presente no stand antes de enviar o pedido.",
  },
];

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
    braceletLabel: "ID de la pulsera",
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
      "Lanza un dado en la siguiente pantalla. Después te preguntaremos qué número salió en tu primera tirada.",
    body:
      "La primera tirada es la que cuenta. Según el número que nos indiques que salió en esa primera tirada, puedes ganar el premio que aparece en la tabla.",
    odds: "1 de cada 100 recibe el pago.",
    prizeTableLabel: "Tabla de premios",
    cta: "Continuar",
  },
  comprehension: {
    eyebrow: "Antes de seguir",
    title: "¿Qué número te pediremos que nos digas después?",
    options: ["Primera tirada", "Última tirada", "La más alta"],
    errorEmpty: "Selecciona una opción",
    errorWrong: "Recuerda: te pediremos el número de la primera tirada",
    cta: "Seguir",
  },
  game: {
    title: "Tirada",
    initialIntro: "Pulsa el dado o el botón Lanzar para hacer tu primera tirada.",
    intro: "Pulsa el dado para ver otra tirada.",
    visibleResultLabel: "",
    firstResultTemplate: "Tu primera tirada: {value}",
    continueCta: "Continuar",
    firstRollCta: "Lanzar",
    rerollCta: "",
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
    body: "Indica el número que te salió al tirar el dado la primera vez tocando ese número.",
    errorSave: "No se pudo guardar la respuesta",
  },
  prizeReveal: {
    eyebrow: "Selección final",
    title: "Clica una",
    helper: "Elige una figura y, si es la premiada, ganas {amount} €.",
    winnerResult: "Esta era la figura premiada. Ganas {amount} €.",
    loserResult: "La figura premiada era otra. El premio era {amount} €.",
    optionLabel: "Ficha",
    footer: "",
  },
  treatment: {
    controlTitle: "Tu respuesta es anónima",
    controlBody: "Selecciona tu número",
    socialMessageTemplate:
      "{count} de cada {denominator} personas eligieron {target}.",
  },
  bonusDraw: {
    title: "Consigue opciones extra para el sorteo VIP",
    intro: "Ya tienes 1 papeleta para el sorteo de 2 entradas VIP por haber participado.",
    prompt:
      "Si quieres una extra, adivina qué número crees que más veces nos dirá la gente que le salió en su primera tirada.",
    baseTicket: "1 papeleta por participar",
    predictionTicket: "1 extra si aciertas la predicción",
    inviteTicket: "1 extra por cada persona del festival que invites y participe",
    achievedLabel: "Conseguida",
    predictionAchieved: "Papeleta extra conseguida",
    selectedTemplate: "Predicción guardada: {value}",
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
      "Sigues participando en el sorteo de 2 entradas VIP.",
    bodyFooter: "Sabrás más sobre el estudio y sus resultados agregados en cotec.es.",
    shareLabel: "Invitar por WhatsApp",
    shareMessageTemplate: "Si estás ahora en Sónar, haz esta prueba de 60 segundos: puedes entrar en el sorteo de 2 entradas VIP para Sónar 2027 y optar a premios en dinero de hasta 60 €. Participa aquí: {link}",
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
    title: "Para recibir un Bizum",
    intro:
      "Tu código ya está preparado. Si quieres recibir un Bizum, introduce tu teléfono y autoriza la gestión del pago. Si prefieres donar el importe a una ONG, puedes hacerlo directamente.",
    codeLabel: "Código",
    phoneLabel: "Teléfono (solo para Bizum)",
    phonePlaceholder: "Escribe tu teléfono",
    messageLabel: "",
    messagePlaceholder: "",
    donationHint: "Si lo prefieres, puedes donar el importe a una ONG sin indicar teléfono ni marcar autorización.",
    lookupLabel: "",
    submitLabel: "Solicitar Bizum",
    donateLabel: "Donar a una ONG",
    consentLabel:
      "Autorizo el tratamiento de mis datos de pago para gestionar el Bizum y confirmo que he leído la información de privacidad.",
    consentInfoLabel: "Más información",
    privacyModalTitle: "Privacidad y gestión ética del pago",
    privacySections: PAYMENT_PRIVACY_SECTIONS_ES,
    success: "Solicitud enviada",
    invalidCode: "Código no válido",
    alreadyUsed: "Código ya usado",
    lookupHelpTemplate: "Código válido · {amount} EUR",
    phoneRequired: "Introduce un teléfono válido para continuar",
    consentRequired:
      "Marca la autorización de privacidad para continuar",
    successEyebrow: "Solicitud enviada",
    successTitle: "Aún puedes ganar",
    successBody: "Tu solicitud de Bizum ha quedado registrada correctamente.",
    successDonationBody:
      "Tu solicitud de donación a una ONG ha quedado registrada correctamente.",
    successSecondary:
      "Además, sigues participando en el sorteo de 2 entradas VIP.",
    successFooter: "Sabrás más sobre el estudio y sus resultados agregados en cotec.es.",
    successShareLabel: "Invitar por WhatsApp",
    successShareMessageTemplate: "Si estás ahora en Sónar, haz esta prueba de 60 segundos: puedes entrar en el sorteo de 2 entradas VIP para Sónar 2027 y optar a premios en dinero de hasta 60 €. Participa aquí: {link}",
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
    braceletLabel: "ID de la polsera",
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
      "Llança un dau a la pantalla següent. Després et preguntarem quin número va sortir a la teva primera tirada.",
    body:
      "La primera tirada és la que compta. Segons el número que ens indiquis que va sortir en aquesta primera tirada, pots guanyar el premi que apareix a la taula.",
    odds: "1 de cada 100 rep el pagament.",
    prizeTableLabel: "Taula de premis",
    cta: "Continuar",
  },
  comprehension: {
    eyebrow: "Abans de seguir",
    title: "Quin número et preguntarem després?",
    options: ["Primera tirada", "Última tirada", "La més alta"],
    errorEmpty: "Selecciona una opció",
    errorWrong: "Recorda: et demanarem el número de la primera tirada",
    cta: "Seguir",
  },
  game: {
    title: "Tirada",
    initialIntro: "Prem el dau o el botó Llançar per fer la teva primera tirada.",
    intro: "Prem el dau per veure una altra tirada.",
    visibleResultLabel: "",
    firstResultTemplate: "La teva primera tirada: {value}",
    continueCta: "Continuar",
    firstRollCta: "Llançar",
    rerollCta: "",
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
    body: "Indica el número que et va sortir en tirar el dau la primera vegada fent-hi clic.",
    errorSave: "No s'ha pogut guardar la resposta",
  },
  prizeReveal: {
    eyebrow: "Selecció final",
    title: "Tria'n una",
    helper: "Tria una figura. Si és la premiada, guanyes {amount} €.",
    winnerResult: "Aquesta era la figura premiada. Guanyes {amount} €.",
    loserResult: "La figura premiada era una altra. El premi era {amount} €.",
    optionLabel: "Fitxa",
    footer: "",
  },
  treatment: {
    controlTitle: "La teva resposta és anònima",
    controlBody: "Selecciona el teu número",
    socialMessageTemplate:
      "{count} de cada {denominator} persones van escollir {target}.",
  },
  bonusDraw: {
    title: "Aconsegueix opcions extra per al sorteig VIP",
    intro: "Ja tens 1 papereta per al sorteig de 2 entrades VIP per haver participat.",
    prompt:
      "Si en vols una extra, endevina quin número creus que la gent ens dirà més vegades que li va sortir en la primera tirada.",
    baseTicket: "1 papereta per participar",
    predictionTicket: "1 extra si encertes la predicció",
    inviteTicket: "1 extra per cada persona del festival que convidis i participi",
    achievedLabel: "Aconseguida",
    predictionAchieved: "Papereta extra aconseguida",
    selectedTemplate: "Predicció desada: {value}",
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
      "Continues participant en el sorteig de 2 entrades VIP.",
    bodyFooter: "Sabràs més sobre l'estudi i els seus resultats agregats a cotec.es.",
    shareLabel: "Convidar per WhatsApp",
    shareMessageTemplate: "Si ets ara al Sónar, prova això: dura 60 segons i pots entrar al sorteig de 2 entrades VIP per al Sónar 2027 i optar a premis en diners de fins a 60 €. Participa aquí: {link}",
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
    title: "Per rebre un Bizum",
    intro:
      "El teu codi ja està preparat. Si vols rebre un Bizum, introdueix el teu telèfon i autoritza la gestió del pagament. Si prefereixes donar l'import a una ONG, ho pots fer directament.",
    codeLabel: "Codi",
    phoneLabel: "Telèfon (només per a Bizum)",
    phonePlaceholder: "Escriu el teu telèfon",
    messageLabel: "",
    messagePlaceholder: "",
    donationHint: "Si ho prefereixes, pots donar l'import a una ONG sense indicar telèfon ni marcar autorització.",
    lookupLabel: "",
    submitLabel: "Sol·licitar Bizum",
    donateLabel: "Donar a una ONG",
    consentLabel:
      "Autoritzo el tractament de les meves dades de pagament per gestionar el Bizum i confirmo que he llegit la informació de privacitat.",
    consentInfoLabel: "Més informació",
    privacyModalTitle: "Privacitat i gestió ètica del pagament",
    privacySections: PAYMENT_PRIVACY_SECTIONS_CA,
    success: "Sol·licitud enviada",
    invalidCode: "Codi no vàlid",
    alreadyUsed: "Codi ja utilitzat",
    lookupHelpTemplate: "Codi vàlid · {amount} EUR",
    phoneRequired: "Introdueix un telèfon vàlid per continuar",
    consentRequired:
      "Marca l'autorització de privacitat per continuar",
    successEyebrow: "Sol·licitud enviada",
    successTitle: "Encara pots guanyar",
    successBody: "La teva sol·licitud de Bizum ha quedat registrada correctament.",
    successDonationBody:
      "La teva sol·licitud de donació a una ONG ha quedat registrada correctament.",
    successSecondary:
      "A més, continues participant en el sorteig de 2 entrades VIP.",
    successFooter: "Sabràs més sobre l'estudi i els seus resultats agregats a cotec.es.",
    successShareLabel: "Convidar per WhatsApp",
    successShareMessageTemplate: "Si ets ara al Sónar, prova això: dura 60 segons i pots entrar al sorteig de 2 entrades VIP per al Sónar 2027 i optar a premis en diners de fins a 60 €. Participa aquí: {link}",
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
    intro: "Roll a die on the next screen. Then we will ask which number came up on your first roll.",
    body:
      "The first roll is the one that counts. Based on the number you tell us came up on that first roll, you may win the prize shown in the table.",
    odds: "1 in 100 receives payment.",
    prizeTableLabel: "Prize table",
    cta: "Continue",
  },
  comprehension: {
    eyebrow: "Before you continue",
    title: "Which number will we ask you about next?",
    options: ["First roll", "Last roll", "The highest one"],
    errorEmpty: "Select one option",
    errorWrong: "Remember: we will ask for the number from the first roll",
    cta: "Continue",
  },
  game: {
    title: "Roll",
    initialIntro: "Tap the die or the Roll button to make your first roll.",
    intro: "Tap the die to see another roll.",
    visibleResultLabel: "",
    firstResultTemplate: "Your first roll: {value}",
    continueCta: "Continue",
    firstRollCta: "Roll",
    rerollCta: "",
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
    body: "Enter the number that came up when you rolled the die the first time by tapping it.",
    errorSave: "Could not save your response",
  },
  prizeReveal: {
    eyebrow: "Final selection",
    title: "Pick one",
    helper: "Choose one figure. If it is the winning one, you get {amount} €.",
    winnerResult: "This was the winning figure. You get {amount} €.",
    loserResult: "A different figure was the winning one. The prize was {amount} €.",
    optionLabel: "Tile",
    footer: "",
  },
  treatment: {
    controlTitle: "Your response is anonymous",
    controlBody: "Select your number",
    socialMessageTemplate:
      "{count} out of every {denominator} people chose {target}.",
  },
  bonusDraw: {
    title: "Get extra entries for the VIP draw",
    intro: "You already have 1 entry for the draw for 2 VIP tickets for taking part.",
    prompt:
      "If you want one extra, guess which number you think people will tell us most often came up on their first roll.",
    baseTicket: "1 entry for taking part",
    predictionTicket: "1 extra if your prediction is correct",
    inviteTicket: "1 extra for each person at the festival you invite who takes part",
    achievedLabel: "Earned",
    predictionAchieved: "Extra entry earned",
    selectedTemplate: "Prediction saved: {value}",
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
      "You are still entered in the draw for 2 VIP tickets.",
    bodyFooter: "You will be able to learn more about the study and its aggregated results at cotec.es.",
    shareLabel: "Invite on WhatsApp",
    shareMessageTemplate: "If you are at Sónar right now, try this: it takes 60 seconds and you can enter the draw for 2 VIP tickets for Sónar 2027 and cash prizes up to 60 €. Join here: {link}",
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
    title: "To receive a Bizum",
    intro:
      "Your code is already prepared. If you want to receive a Bizum, enter your phone number and authorise payment processing. If you prefer to donate the amount to an NGO, you can do that directly.",
    codeLabel: "Code",
    phoneLabel: "Phone (Bizum only)",
    phonePlaceholder: "Enter your phone number",
    messageLabel: "",
    messagePlaceholder: "",
    donationHint: "If you prefer, you can donate the amount to an NGO without entering a phone number or ticking the authorisation.",
    lookupLabel: "",
    submitLabel: "Request Bizum",
    donateLabel: "Donate to an NGO",
    consentLabel:
      "I authorise the processing of my payment data to manage the Bizum and confirm that I have read the privacy information.",
    consentInfoLabel: "More information",
    privacyModalTitle: "Privacy and ethical payment handling",
    privacySections: PAYMENT_PRIVACY_SECTIONS_EN,
    success: "Request sent",
    invalidCode: "Invalid code",
    alreadyUsed: "Code already used",
    lookupHelpTemplate: "Valid code · {amount} EUR",
    phoneRequired: "Enter a valid phone number to continue",
    consentRequired:
      "Tick the privacy authorisation to continue",
    successEyebrow: "Request sent",
    successTitle: "You can still win",
    successBody: "Your Bizum request has been recorded successfully.",
    successDonationBody:
      "Your NGO donation request has been recorded successfully.",
    successSecondary:
      "You are also still entered in the draw for 2 VIP tickets.",
    successFooter: "You will be able to learn more about the study and its aggregated results at cotec.es.",
    successShareLabel: "Invite on WhatsApp",
    successShareMessageTemplate: "If you are at Sónar right now, try this: it takes 60 seconds and you can enter the draw for 2 VIP tickets for Sónar 2027 and cash prizes up to 60 €. Join here: {link}",
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
      "Lancez un dé sur l'écran suivant. Ensuite, nous vous demanderons quel nombre est sorti lors de votre premier lancer.",
    body:
      "Le premier lancer est celui qui compte. Selon le nombre que vous nous indiquerez comme étant sorti lors de ce premier lancer, vous pourrez gagner le prix affiché dans le tableau.",
    odds: "1 personne sur 100 reçoit le paiement.",
    prizeTableLabel: "Table des prix",
    cta: "Continuer",
  },
  comprehension: {
    eyebrow: "Avant de continuer",
    title: "Quel nombre vous demanderons-nous ensuite ?",
    options: ["Premier lancer", "Dernier lancer", "Le plus élevé"],
    errorEmpty: "Sélectionnez une option",
    errorWrong: "Rappelez-vous : nous vous demanderons le nombre du premier lancer",
    cta: "Continuer",
  },
  game: {
    title: "Lancer",
    initialIntro: "Touchez le dé ou le bouton Lancer pour faire votre premier lancer.",
    intro: "Touchez le dé pour voir un autre lancer.",
    visibleResultLabel: "",
    firstResultTemplate: "Votre premier lancer : {value}",
    continueCta: "Continuer",
    firstRollCta: "Lancer",
    rerollCta: "",
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
    body: "Indiquez le nombre obtenu lorsque vous avez lancé le dé la première fois en cliquant dessus.",
    errorSave: "Impossible d'enregistrer la réponse",
  },
  prizeReveal: {
    eyebrow: "Sélection finale",
    title: "Choisissez-en une",
    helper: "Choisissez une figure. Si c'est la figure gagnante, vous gagnez {amount} €.",
    winnerResult: "C'était la figure gagnante. Vous gagnez {amount} €.",
    loserResult: "La figure gagnante était une autre. Le prix était de {amount} €.",
    optionLabel: "Case",
    footer: "",
  },
  treatment: {
    controlTitle: "Votre réponse est anonyme",
    controlBody: "Sélectionnez votre nombre",
    socialMessageTemplate:
      "{count} personnes sur {denominator} ont choisi {target}.",
  },
  bonusDraw: {
    title: "Obtenez des chances supplémentaires pour le tirage VIP",
    intro: "Vous avez déjà 1 participation au tirage de 2 billets VIP pour avoir pris part à l'activité.",
    prompt:
      "Si vous en voulez une de plus, devinez quel nombre, selon vous, les personnes nous diront le plus souvent avoir obtenu à leur premier lancer.",
    baseTicket: "1 participation pour avoir pris part",
    predictionTicket: "1 supplémentaire si votre prédiction est correcte",
    inviteTicket: "1 supplémentaire par personne du festival que vous invitez et qui participe",
    achievedLabel: "Obtenue",
    predictionAchieved: "Participation supplémentaire obtenue",
    selectedTemplate: "Prédiction enregistrée : {value}",
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
      "Vous participez toujours au tirage de 2 billets VIP.",
    bodyFooter: "Vous en saurez plus sur l'étude et ses résultats agrégés sur cotec.es.",
    shareLabel: "Inviter sur WhatsApp",
    shareMessageTemplate: "Si vous êtes au Sónar en ce moment, essayez ceci : cela dure 60 secondes et vous pouvez participer au tirage de 2 billets VIP pour le Sónar 2027 ainsi qu'à des prix en argent jusqu'à 60 €. Participez ici : {link}",
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
    title: "Pour recevoir un Bizum",
    intro:
      "Votre code est déjà prêt. Si vous souhaitez recevoir un Bizum, indiquez votre numéro de téléphone et autorisez le traitement du paiement. Si vous préférez faire don du montant à une ONG, vous pouvez le faire directement.",
    codeLabel: "Code",
    phoneLabel: "Téléphone (Bizum uniquement)",
    phonePlaceholder: "Saisissez votre téléphone",
    messageLabel: "",
    messagePlaceholder: "",
    donationHint: "Si vous le préférez, vous pouvez faire don du montant à une ONG sans indiquer de téléphone ni cocher l'autorisation.",
    lookupLabel: "",
    submitLabel: "Demander un Bizum",
    donateLabel: "Faire un don à une ONG",
    consentLabel:
      "J'autorise le traitement de mes données de paiement pour gérer le Bizum et je confirme avoir lu les informations de confidentialité.",
    consentInfoLabel: "Plus d'information",
    privacyModalTitle: "Confidentialité et gestion éthique du paiement",
    privacySections: PAYMENT_PRIVACY_SECTIONS_FR,
    success: "Demande envoyée",
    invalidCode: "Code invalide",
    alreadyUsed: "Code déjà utilisé",
    lookupHelpTemplate: "Code valide · {amount} EUR",
    phoneRequired: "Entrez un numéro de téléphone valide pour continuer",
    consentRequired:
      "Cochez l'autorisation de confidentialité pour continuer",
    successEyebrow: "Demande envoyée",
    successTitle: "Vous pouvez encore gagner",
    successBody: "Votre demande de Bizum a bien été enregistrée.",
    successDonationBody:
      "Votre demande de don à une ONG a bien été enregistrée.",
    successSecondary:
      "Vous participez aussi toujours au tirage de 2 billets VIP.",
    successFooter: "Vous en saurez plus sur l'étude et ses résultats agrégés sur cotec.es.",
    successShareLabel: "Inviter sur WhatsApp",
    successShareMessageTemplate: "Si vous êtes au Sónar en ce moment, essayez ceci : cela dure 60 secondes et vous pouvez participer au tirage de 2 billets VIP pour le Sónar 2027 ainsi qu'à des prix en argent jusqu'à 60 €. Participez ici : {link}",
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
      "Lança um dado no ecrã seguinte. Depois vamos perguntar que número saiu na tua primeira tirada.",
    body:
      "A primeira tirada é a que conta. Consoante o número que nos disseres que saiu nessa primeira tirada, poderás ganhar o prémio que aparece na tabela.",
    odds: "1 em cada 100 recebe o pagamento.",
    prizeTableLabel: "Tabela de prémios",
    cta: "Continuar",
  },
  comprehension: {
    eyebrow: "Antes de continuar",
    title: "Que número te vamos perguntar depois?",
    options: ["Primeira tirada", "Última tirada", "A mais alta"],
    errorEmpty: "Seleciona uma opção",
    errorWrong: "Lembra-te: vamos pedir o número da primeira tirada",
    cta: "Seguir",
  },
  game: {
    title: "Tirada",
    initialIntro: "Toca no dado ou no botão Lançar para fazer a tua primeira tirada.",
    intro: "Toca no dado para ver outra tirada.",
    visibleResultLabel: "",
    firstResultTemplate: "A tua primeira tirada: {value}",
    continueCta: "Continuar",
    firstRollCta: "Lançar",
    rerollCta: "",
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
    body: "Indica o número que te saiu ao lançar o dado na primeira vez clicando nele.",
    errorSave: "Não foi possível guardar a resposta",
  },
  prizeReveal: {
    eyebrow: "Seleção final",
    title: "Escolhe uma",
    helper: "Escolhe uma figura. Se for a premiada, ganhas {amount} €.",
    winnerResult: "Esta era a figura premiada. Ganhas {amount} €.",
    loserResult: "A figura premiada era outra. O prémio era de {amount} €.",
    optionLabel: "Ficha",
    footer: "",
  },
  treatment: {
    controlTitle: "A tua resposta é anónima",
    controlBody: "Seleciona o teu número",
    socialMessageTemplate:
      "{count} de cada {denominator} pessoas escolheram {target}.",
  },
  bonusDraw: {
    title: "Consegue entradas extra para o sorteio VIP",
    intro: "Já tens 1 participação no sorteio de 2 entradas VIP por teres participado.",
    prompt:
      "Se quiseres mais uma, adivinha qual é o número que achas que as pessoas nos vão dizer mais vezes que lhes saiu na primeira tirada.",
    baseTicket: "1 participação por participar",
    predictionTicket: "1 extra se acertares na previsão",
    inviteTicket: "1 extra por cada pessoa do festival que convidares e que participe",
    achievedLabel: "Conseguida",
    predictionAchieved: "Participação extra conseguida",
    selectedTemplate: "Previsão guardada: {value}",
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
      "Continuas a participar no sorteio de 2 entradas VIP.",
    bodyFooter: "Saberás mais sobre o estudo e os seus resultados agregados em cotec.es.",
    shareLabel: "Convidar por WhatsApp",
    shareMessageTemplate: "Se estás agora no Sónar, experimenta isto: demora 60 segundos e podes entrar no sorteio de 2 entradas VIP para o Sónar 2027 e optar a prémios em dinheiro até 60 €. Participa aqui: {link}",
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
    title: "Para receber um Bizum",
    intro:
      "O teu código já está preparado. Se quiseres receber um Bizum, introduz o teu telefone e autoriza a gestão do pagamento. Se preferires doar o valor a uma ONG, podes fazê-lo diretamente.",
    codeLabel: "Código",
    phoneLabel: "Telefone (apenas para Bizum)",
    phonePlaceholder: "Escreve o teu telefone",
    messageLabel: "",
    messagePlaceholder: "",
    donationHint: "Se preferires, podes doar o valor a uma ONG sem indicar telefone nem marcar autorização.",
    lookupLabel: "",
    submitLabel: "Pedir Bizum",
    donateLabel: "Doar a uma ONG",
    consentLabel:
      "Autorizo o tratamento dos meus dados de pagamento para gerir o Bizum e confirmo que li a informação de privacidade.",
    consentInfoLabel: "Mais informação",
    privacyModalTitle: "Privacidade e gestão ética do pagamento",
    privacySections: PAYMENT_PRIVACY_SECTIONS_PT,
    success: "Pedido enviado",
    invalidCode: "Código inválido",
    alreadyUsed: "Código já usado",
    lookupHelpTemplate: "Código válido · {amount} EUR",
    phoneRequired: "Introduz um telefone válido para continuar",
    consentRequired:
      "Marca a autorização de privacidade para continuar",
    successEyebrow: "Pedido enviado",
    successTitle: "Ainda podes ganhar",
    successBody: "O teu pedido de Bizum ficou registado corretamente.",
    successDonationBody:
      "O teu pedido de doação a uma ONG ficou registado corretamente.",
    successSecondary:
      "Além disso, continuas a participar no sorteio de 2 entradas VIP.",
    successFooter: "Saberás mais sobre o estudo e os seus resultados agregados em cotec.es.",
    successShareLabel: "Convidar por WhatsApp",
    successShareMessageTemplate: "Se estás agora no Sónar, experimenta isto: demora 60 segundos e podes entrar no sorteio de 2 entradas VIP para o Sónar 2027 e optar a prémios em dinheiro até 60 €. Participa aqui: {link}",
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

const it = withServerErrors({
  ...en,
  common: {
    ...en.common,
    languageSelectorAria: "Seleziona la lingua",
    loadingResume: "Recupero sessione",
    loadingPrepare: "Preparazione esperienza",
    close: "Chiudi",
  },
  languageEntry: {
    ...en.languageEntry,
    subtitle: "Select your language",
  },
  landing: {
    ...en.landing,
    eyebrow: "Partecipa, 60 sec, e sorteggiamo:",
    title:
      "2 biglietti VIP per SONAR 2027\ne centinaia di premi fino a 60 euro",
    braceletLabel: "ID del braccialetto",
    braceletPlaceholder: "Es: 10000001",
    moreInfoButton: "Piu informazioni",
    ageCheckbox: "Ho 18 anni o piu",
    participationCheckbox: "Accetto di partecipare",
    dataCheckbox: "Accetto il trattamento dei dati",
    cta: "Inizia",
  },
  instructions: {
    ...en.instructions,
    title: "Come funziona",
    intro:
      "Lancia un dado nella schermata successiva. Poi ti chiederemo quale numero e uscito al primo lancio.",
    body:
      "Il primo lancio e quello che conta. In base al numero che ci dirai essere uscito in quel primo lancio, puoi vincere il premio che appare nella tabella.",
    odds: "1 persona su 100 riceve il pagamento.",
    prizeTableLabel: "Tabella dei premi",
    cta: "Continua",
  },
  comprehension: {
    ...en.comprehension,
    eyebrow: "Prima di continuare",
    title: "Quale numero ti chiederemo dopo?",
    options: ["Primo lancio", "Ultimo lancio", "Il piu alto"],
    errorEmpty: "Seleziona un'opzione",
    errorWrong: "Ricorda: ti chiederemo il numero del primo lancio",
    cta: "Continua",
  },
  game: {
    ...en.game,
    title: "Lancio",
    initialIntro: "Tocca il dado o il pulsante Lancia per fare il primo lancio.",
    intro: "Tocca il dado per vedere un altro lancio.",
    firstResultTemplate: "Il tuo primo lancio: {value}",
    continueCta: "Continua",
    firstRollCta: "Lancia",
    rerollCta: "",
    loading: "Caricamento...",
    errors: {
      ...en.game.errors,
      noSession: "Sessione non disponibile",
      loadRoll: "Impossibile lanciare il dado",
      loadReport: "Azione non disponibile",
    },
  },
  report: {
    ...en.report,
    title: "Il tuo primo lancio",
    body: "Indica il numero uscito quando hai lanciato il dado la prima volta facendo clic su di esso.",
    errorSave: "Impossibile salvare la risposta",
  },
  prizeReveal: {
    ...en.prizeReveal,
    eyebrow: "Selezione finale",
    title: "Scegline una",
    helper: "Scegli una figura. Se e quella premiata, vinci {amount} euro.",
    winnerResult: "Questa era la figura premiata. Vinci {amount} euro.",
    loserResult: "La figura premiata era un'altra. Il premio era di {amount} euro.",
    optionLabel: "Casella",
  },
  winner: {
    ...en.winner,
    eyebrow: "Sei stato selezionato",
    title: "Pagamento confermato",
    amountLabel: "Premio in denaro",
    codeLabelTemplate: "Codice di riscossione: {code}",
    cta: "Richiedi il Bizum",
  },
  loser: {
    ...en.loser,
    eyebrow: "Grazie per aver partecipato",
    title: "Puoi ancora vincere",
    body: "Non sei stato selezionato per il premio in denaro.",
    bodySecondary: "Continui a partecipare al sorteggio di 2 biglietti VIP.",
    bodyFooter: "Saprai di piu sullo studio e sui risultati aggregati su cotec.es.",
    shareLabel: "Invita via WhatsApp",
    shareMessageTemplate:
      "Se sei al Sónar in questo momento, prova questo: ti richiede 60 secondi e puoi entrare nel sorteggio di 2 biglietti VIP per il Sónar 2027 e concorrere a premi in denaro fino a 60 euro. Partecipa qui: {link}",
  },
  paused: {
    ...en.paused,
    eyebrow: "Grazie",
    title: "Tutti i premi sono gia stati distribuiti",
    body: "L'attivita e chiusa per ora.",
    bodySecondary:
      "Se vuoi ricevere avvisi su studi simili, lascia la tua email.",
    emailLabel: "Email",
    emailPlaceholder: "nome@email.com",
    cta: "Avvisami",
    success: "Ti avviseremo se apriremo un nuovo studio.",
  },
  paymentPage: {
    ...en.paymentPage,
    eyebrow: "Ricevi il tuo premio",
    title: "Per ricevere un Bizum",
    intro: "",
    codeLabel: "Codice del premio",
    phoneLabel: "Il tuo telefono",
    phonePlaceholder: "Scrivi il tuo telefono",
    donationHint:
      "Se preferisci, puoi donare l'importo a una ONG senza inserire il telefono ne segnare l'autorizzazione.",
    submitLabel: "Richiedi Bizum",
    donateLabel: "Dona a una ONG",
    consentLabel:
      "Autorizzo il trattamento dei miei dati di pagamento per gestire il Bizum e confermo di aver letto l'informativa sulla privacy.",
    consentInfoLabel: "Piu informazioni",
    privacyModalTitle: "Privacy e gestione etica del pagamento",
    privacySections: PAYMENT_PRIVACY_SECTIONS_EN,
    success: "Richiesta inviata",
    invalidCode: "Codice non valido",
    alreadyUsed: "Codice gia usato",
    lookupHelpTemplate: "Codice valido · {amount} EUR",
    phoneRequired: "Inserisci un telefono valido per continuare",
    consentRequired:
      "Segna l'autorizzazione privacy per continuare",
    successEyebrow: "Richiesta inviata",
    successTitle: "Puoi ancora vincere",
    successBody: "La tua richiesta di Bizum e stata registrata correttamente.",
    successDonationBody:
      "La tua richiesta di donazione a una ONG e stata registrata correttamente.",
    successSecondary:
      "Inoltre continui a partecipare al sorteggio di 2 biglietti VIP.",
    successFooter:
      "Saprai di piu sullo studio e sui suoi risultati aggregati su cotec.es.",
    successShareLabel: "Invita via WhatsApp",
    successShareMessageTemplate:
      "Se sei al Sónar in questo momento, prova questo: ti richiede 60 secondi e puoi entrare nel sorteggio di 2 biglietti VIP per il Sónar 2027 e concorrere a premi in denaro fino a 60 euro. Partecipa qui: {link}",
    errorDefault: "Errore durante l'invio",
  },
  accessibility: {
    ...en.accessibility,
    diceRollAria: "Lancia il dado",
  },
  errors: {
    braceletNotFound: "Braccialetto non trovato",
    accessInvalid: "Accesso non valido",
    sessionNotFound: "Sessione non trovata",
    actionUnavailable: "Azione non disponibile",
    defaultMessage: "Errore imprevisto",
  },
});

export const UI_LEXICON: Record<AppLanguage, UiCopy> = {
  es,
  ca,
  en,
  fr,
  pt,
  it,
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

