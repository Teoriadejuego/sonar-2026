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
    continueLabel: string;
    finalClosingMessage: string;
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
    subtitle: string;
    listLabel: string;
    steps: string[];
    intro: string;
    body: string;
    odds: string;
    prizeTableLabel: string;
    cta: string;
  };
  comprehension: {
    eyebrow: string;
    title: string;
    body: string;
    odds: string;
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
    recallTicket: string;
    inviteTicket: string;
    achievedLabel: string;
    predictionAchieved: string;
    selectedTemplate: string;
    recallPrompt: string;
    recallOptions: [string, string, string];
    recallPlaceholder: string;
    recallCta: string;
    recallSavedTemplate: string;
    recallError: string;
    saveError: string;
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
    braceletLabel: string;
    braceletPlaceholder: string;
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
    braceletRequired: string;
    braceletMismatch: string;
    consentRequired: string;
    successEyebrow: string;
    successTitle: string;
    successBody: string;
    successDonationBody: string;
    successSkipBody: string;
    successSecondary: string;
    successFooter: string;
    successShareLabel: string;
    successShareMessageTemplate: string;
    skipMismatchLabel: string;
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
      "El formato de pulsera no es valido. Usa 8 caracteres con 4 letras y 4 numeros.":
        seed.errors.accessInvalid,
      "Pulsera erronea, no coincide con la registrada inicialmente.":
        seed.errors.actionUnavailable,
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
    continueLabel: "Continuar",
    finalClosingMessage:
      "Muchas gracias, has terminado. Cierra el navegador y disfruta de la experiencia SONAR 2026.",
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
    braceletPlaceholder: "Ej: AB12CD34",
    moreInfoButton: "Más información",
    ageCheckbox: "Confirmo que tengo 18 años o más",
    participationCheckbox: "He leído la información y acepto participar",
    dataCheckbox: "He leído y acepto el tratamiento de datos",
    cta: "Comenzar",
    footer: "",
    errors: {
      braceletRequired: "Introduce el ID de tu pulsera.",
      consentsRequired: "Marca las tres casillas para continuar.",
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
          "Introducirás el código de tu pulsera, verás una tirada de dado y después indicarás qué número salió. El proceso dura alrededor de un minuto.",
      },
      {
        title: "Pago e incentivos",
        body:
          "La asignación del pago se realiza automáticamente. Si resultas seleccionado, el importe depende del número que indiques y se gestiona al final de la actividad.",
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
    title: "¡Gracias por participar!",
    subtitle:
      "Solo por participar entras en un sorteo para una entrada del SONAR 2027.",
    listLabel: "Instrucciones:",
    steps: [
      "En la primera pantalla verás los premios del juego.",
      "En la siguiente, encontrarás un dado.",
      "Dale a “Lanzar”.",
      "Memoriza el número.",
      "Luego vas a indicar el número.",
      "Y al final verás el dinero que has ganado.",
    ],
    intro:
      "En la primera pantalla verás los premios del juego y después pasarás al dado.",
    body: "La pregunta posterior siempre se refiere al primer número.",
    odds: "",
    prizeTableLabel: "Instrucciones",
    cta: "Continuar",
  },
  comprehension: {
    eyebrow: "",
    title: "Tabla de premios:",
    body: "Cada número se asocia con un premio.",
    odds: "Uno de cada cien ganará el dinero de verdad (bizum).",
    options: [
      "Indicar qué número salió",
      "Elegir el premio que prefieres",
      "Pasar a la siguiente pantalla",
    ],
    errorEmpty: "",
    errorWrong: "",
    cta: "Continuar",
  },
  game: {
    title: "Lanza el dado",
    initialIntro: "Dale a “Lanzar” y memoriza el primer número.",
    intro:
      "Cuando tengas claro el número, continúa.",
    visibleResultLabel: "",
    firstResultTemplate: "Número obtenido: {value}",
    continueCta: "Continuar",
    firstRollCta: "Lanzar",
    rerollCta: "Lanzar",
    loading: "Cargando...",
    attemptsTemplate: "Tirada registrada: {count}",
    errors: {
      noSession: "No hay una sesión activa.",
      loadRoll: "No se pudo cargar la tirada.",
      loadReport: "No se pudo continuar.",
    },
  },
  report: {
    title: "¿Qué te salió en la primera tirada?",
    body: "Selecciona el número que te salió en la primera tirada.",
    errorSave: "No se pudo guardar tu respuesta.",
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
    controlBody: "Indica qué número salió.",
    socialMessageTemplate:
      "{count} de {denominator} participantes anteriores dijeron que les salió un {target}.",
  },
  bonusDraw: {
    title: "Consigue opciones extra para el sorteo de SONAR 2027",
    intro: "Ya tienes 1 papeleta para el sorteo de 2 entradas para SONAR 2027 por haber participado.",
    prompt:
      "¿Qué número crees que nos dirá más veces la gente?",
    baseTicket: "1 papeleta por participar",
    predictionTicket: "1 extra si aciertas la predicción",
    recallTicket: "1 extra si recuerdas el mensaje",
    inviteTicket: "1 extra por cada persona del festival que invites y participe",
    achievedLabel: "Conseguida",
    predictionAchieved: "Papeleta extra conseguida",
    selectedTemplate: "Predicción guardada: {value}",
    recallPrompt:
      "¿Cuánta gente te dijimos que había elegido el 6 de 60 participantes anteriores?",
    recallOptions: ["0-20", "21-40", "41-60"],
    recallPlaceholder: "Escribe un número de 0 a 60",
    recallCta: "Guardar",
    recallSavedTemplate: "Respuesta guardada: {value}",
    recallError: "Escribe un número entre 0 y 60.",
    saveError: "No se pudo guardar. Inténtalo de nuevo.",
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
    title: "Resultados",
    body: "No has sido seleccionado para el premio económico.",
    bodySecondary:
      "Sigues participando en el sorteo de 2 entradas para SONAR 2027.",
    bodyFooter: "Podrás consultar más información sobre el estudio y sus resultados agregados en cotec.es, y el código ganador al final del festival.",
    shareLabel: "Invitar por WhatsApp",
    shareMessageTemplate: "Si estás ahora mismo en Sónar, prueba esta actividad: dura 60 segundos y puedes entrar en el sorteo de 2 entradas para Sónar 2027 y optar a premios en dinero de hasta 60 €. Participa aquí: {link}",
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
    braceletLabel: "ID de la pulsera",
    braceletPlaceholder: "Ej: AB12CD34",
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
    braceletRequired: "Introduce el ID de la pulsera",
    braceletMismatch:
      "Pulsera errónea, no coincide con la registrada inicialmente.",
    consentRequired:
      "Marca la autorización de privacidad para continuar",
    successEyebrow: "Solicitud enviada",
    successTitle: "Aún puedes ganar",
    successBody: "Tu solicitud de Bizum ha quedado registrada correctamente.",
    successDonationBody:
      "Tu solicitud de donación a una ONG ha quedado registrada correctamente.",
    successSkipBody:
      "Tu participación ya ha quedado registrada. Puedes continuar sin reclamar el premio.",
    successSecondary:
      "Además, sigues participando en el sorteo de 2 entradas VIP.",
    successFooter: "Sabrás más sobre el estudio y sus resultados agregados en cotec.es, y el código ganador al finalizar el festival.",
    successShareLabel: "Invitar por WhatsApp",
    successShareMessageTemplate: "Si estás ahora en Sónar, haz esta prueba de 60 segundos: puedes entrar en el sorteo de 2 entradas VIP para Sónar 2027 y optar a premios en dinero de hasta 60 €. Participa aquí: {link}",
    skipMismatchLabel: "Continuar sin reclamar premio",
    errorDefault: "Error al enviar",
  },
  accessibility: {
    diceRollAria: "Lanzar dado",
  },
  errors: {
    braceletNotFound: "Pulsera no encontrada.",
    accessInvalid: "Acceso no válido.",
    sessionNotFound: "Sesión no encontrada.",
    actionUnavailable: "Esta acción no está disponible.",
    defaultMessage: "Ha ocurrido un error inesperado.",
  },
});

const ca = withServerErrors({
  common: {
    appTitle: "SONAR 2026",
    languageSelectorAria: "Seleccionar idioma",
    loadingResume: "Recuperant sessió",
    loadingPrepare: "Preparant experiència",
    close: "Tancar",
    continueLabel: "Continuar",
    finalClosingMessage:
      "Moltes gràcies, ja has acabat. Tanca el navegador i gaudeix de l'experiència SONAR 2026.",
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
    braceletPlaceholder: "Ex: AB12CD34",
    moreInfoButton: "Més informació",
    ageCheckbox: "Confirmo que tinc 18 anys o més",
    participationCheckbox: "He llegit la informació i accepto participar",
    dataCheckbox: "He llegit i accepto el tractament de dades",
    cta: "Començar",
    footer: "",
    errors: {
      braceletRequired: "Introdueix l'ID de la polsera.",
      consentsRequired: "Marca les tres caselles per continuar.",
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
      "Introduiràs el codi de la polsera, veuràs una tirada del dau i després indicaràs quin número ha sortit. El procés dura aproximadament un minut.",
      },
      {
        title: "Pagament i incentius",
        body:
          "L'assignació del pagament es fa automàticament. Si resultes seleccionat, l'import depèn del número que indiquis i es tramita al final de l'activitat.",
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
    title: "Gràcies per participar!",
    subtitle:
      "Només per participar entres en un sorteig per a una entrada del SONAR 2027.",
    listLabel: "Instruccions:",
    steps: [
      "A la primera pantalla veuràs els premis del joc.",
      "A la següent, hi trobaràs un dau.",
      "Prem “Llançar”.",
      "Memoritza el número.",
      "Després hauràs d’indicar el número.",
      "I al final veuràs els diners que has guanyat.",
    ],
    intro:
      "A la primera pantalla veuràs els premis del joc i després passaràs al dau.",
    body:
      "La pregunta posterior sempre fa referència al primer número.",
    odds: "",
    prizeTableLabel: "Instruccions",
    cta: "Continuar",
  },
  comprehension: {
    eyebrow: "",
    title: "Taula de premis:",
    body: "Cada número s’associa amb un premi.",
    odds: "Una de cada cent persones guanyarà els diners de veritat (Bizum).",
    options: [
      "Indicar quin número ha sortit",
      "Triar el premi que prefereixes",
      "Passar a la pantalla següent",
    ],
    errorEmpty: "",
    errorWrong: "",
    cta: "Continuar",
  },
  game: {
    title: "Llança el dau",
    initialIntro: "Prem “Llançar” i memoritza el primer número.",
    intro:
      "Quan tinguis clar el número, continua.",
    visibleResultLabel: "",
    firstResultTemplate: "Número obtingut: {value}",
    continueCta: "Continuar",
    firstRollCta: "Llançar",
    rerollCta: "Llançar",
    loading: "Carregant...",
    attemptsTemplate: "Tirada registrada: {count}",
    errors: {
      noSession: "No hi ha cap sessió activa.",
      loadRoll: "No s'ha pogut carregar la tirada.",
      loadReport: "No s'ha pogut continuar.",
    },
  },
  report: {
    title: "Què t’ha sortit a la primera tirada?",
    body: "Selecciona el número que t’ha sortit a la primera tirada.",
    errorSave: "No s'ha pogut desar la teva resposta.",
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
    controlBody: "Indica quin número ha sortit.",
    socialMessageTemplate:
      "{count} de {denominator} participants anteriors van dir que els havia sortit un {target}.",
  },
  bonusDraw: {
    title: "Aconsegueix opcions extra per al sorteig de SONAR 2027",
    intro: "Ja tens 1 papereta per al sorteig de 2 entrades per a SONAR 2027 per haver participat.",
    prompt:
      "Quin número creus que la gent ens dirà més vegades?",
    baseTicket: "1 papereta per participar",
    predictionTicket: "1 extra si encertes la predicció",
    recallTicket: "1 extra si recordes el missatge",
    inviteTicket: "1 extra per cada persona del festival que convidis i participi",
    achievedLabel: "Aconseguida",
    predictionAchieved: "Papereta extra aconseguida",
    selectedTemplate: "Predicció desada: {value}",
    recallPrompt:
      "Quanta gent et vam dir que havia triat el 6 entre 60 participants anteriors?",
    recallOptions: ["0-20", "21-40", "41-60"],
    recallPlaceholder: "Escriu un número de 0 a 60",
    recallCta: "Desar",
    recallSavedTemplate: "Resposta desada: {value}",
    recallError: "Escriu un número entre 0 i 60.",
    saveError: "No s'ha pogut desar. Torna-ho a provar.",
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
    title: "Resultats",
    body: "No has estat seleccionat per al premi econòmic.",
    bodySecondary:
      "Continues participant en el sorteig de 2 entrades per al SONAR 2027.",
    bodyFooter: "Podràs consultar més informació sobre l'estudi i els seus resultats agregats a cotec.es, i el codi guanyador al final del festival.",
    shareLabel: "Convidar per WhatsApp",
    shareMessageTemplate: "Si ets ara mateix al Sónar, prova aquesta activitat: dura 60 segons i pots entrar al sorteig de 2 entrades per al Sónar 2027 i optar a premis en diners de fins a 60 €. Participa aquí: {link}",
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
    braceletLabel: "ID de la polsera",
    braceletPlaceholder: "Ex: AB12CD34",
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
    braceletRequired: "Introdueix l'ID de la polsera",
    braceletMismatch:
      "Polsera errònia, no coincideix amb la registrada inicialment.",
    consentRequired:
      "Marca l'autorització de privacitat per continuar",
    successEyebrow: "Sol·licitud enviada",
    successTitle: "Encara pots guanyar",
    successBody: "La teva sol·licitud de Bizum ha quedat registrada correctament.",
    successDonationBody:
      "La teva sol·licitud de donació a una ONG ha quedat registrada correctament.",
    successSkipBody:
      "La teva participació ja ha quedat registrada. Pots continuar sense reclamar el premi.",
    successSecondary:
      "A més, continues participant en el sorteig de 2 entrades VIP.",
    successFooter: "Sabràs més sobre l'estudi i els seus resultats agregats a cotec.es, i el codi guanyador en acabar el festival.",
    successShareLabel: "Convidar per WhatsApp",
    successShareMessageTemplate: "Si ets ara al Sónar, prova això: dura 60 segons i pots entrar al sorteig de 2 entrades VIP per al Sónar 2027 i optar a premis en diners de fins a 60 €. Participa aquí: {link}",
    skipMismatchLabel: "Continuar sense reclamar el premi",
    errorDefault: "Error en enviar",
  },
  accessibility: {
    diceRollAria: "Llançar dau",
  },
  errors: {
    braceletNotFound: "Polsera no trobada.",
    accessInvalid: "Accés no vàlid.",
    sessionNotFound: "Sessió no trobada.",
    actionUnavailable: "Aquesta acció no està disponible.",
    defaultMessage: "Hi ha hagut un error inesperat.",
  },
});

const en = withServerErrors({
  common: {
    appTitle: "SONAR 2026",
    languageSelectorAria: "Select language",
    loadingResume: "Restoring session",
    loadingPrepare: "Preparing experience",
    close: "Close",
    continueLabel: "Continue",
    finalClosingMessage:
      "Thank you very much, you have finished. Close the browser and enjoy the SONAR 2026 experience.",
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
    braceletPlaceholder: "Eg: AB12CD34",
    moreInfoButton: "More information",
    ageCheckbox: "I confirm that I am 18 or over",
    participationCheckbox: "I have read the information and agree to take part",
    dataCheckbox: "I have read and agree to the data processing",
    cta: "Start",
    footer: "",
    errors: {
      braceletRequired: "Enter your bracelet ID.",
      consentsRequired: "Tick all three boxes to continue.",
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
          "You will enter your bracelet code, see a die roll, and then report which number came up. The process takes about one minute.",
      },
      {
        title: "Payment and incentives",
        body:
          "Payment eligibility is assigned automatically. If you are selected, the amount depends on the number you report and is handled at the end of the activity.",
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
    title: "Thanks for taking part!",
    subtitle:
      "Just for taking part, you enter a draw for a SONAR 2027 ticket.",
    listLabel: "Instructions:",
    steps: [
      "On the first screen you will see the prizes in the game.",
      "On the next one, you will find a die.",
      "Tap “Roll”.",
      "Remember the number.",
      "Then you will report the number.",
      "And at the end you will see how much money you won.",
    ],
    intro:
      "On the first screen you will see the prizes in the game, and then you will move on to the die.",
    body:
      "The later question always refers to the first number.",
    odds: "",
    prizeTableLabel: "Instructions",
    cta: "Continue",
  },
  comprehension: {
    eyebrow: "",
    title: "Prize table:",
    body: "Each number is linked to a prize.",
    odds: "One in every hundred people will receive the real payment (Bizum).",
    options: [
      "Report which number came up",
      "Choose the prize you prefer",
      "Move to the next screen",
    ],
    errorEmpty: "",
    errorWrong: "",
    cta: "Continue",
  },
  game: {
    title: "Roll the die",
    initialIntro: "Tap “Roll” and remember the first number.",
    intro:
      "When you have the number clear, continue.",
    visibleResultLabel: "",
    firstResultTemplate: "Number obtained: {value}",
    continueCta: "Continue",
    firstRollCta: "Roll",
    rerollCta: "Roll",
    loading: "Loading...",
    attemptsTemplate: "Recorded roll: {count}",
    errors: {
      noSession: "There is no active session.",
      loadRoll: "Could not load the roll.",
      loadReport: "Could not continue.",
    },
  },
  report: {
    title: "What came up on the first roll?",
    body: "Select the number that came up on the first roll.",
    errorSave: "Could not save your response.",
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
    controlBody: "Report which number came up.",
    socialMessageTemplate:
      "{count} out of {denominator} earlier participants said they got a {target}.",
  },
  bonusDraw: {
    title: "Get extra entries for the SONAR 2027 draw",
    intro: "You already have 1 entry for the draw for 2 tickets to SONAR 2027 for taking part.",
    prompt:
      "Which number do you think people will report most often?",
    baseTicket: "1 entry for taking part",
    predictionTicket: "1 extra if your prediction is correct",
    recallTicket: "1 extra if you remember the message",
    inviteTicket: "1 extra for each person at the festival you invite who takes part",
    achievedLabel: "Earned",
    predictionAchieved: "Extra entry earned",
    selectedTemplate: "Prediction saved: {value}",
    recallPrompt:
      "How many people did we say had chosen 6 out of 60 earlier participants?",
    recallOptions: ["0-20", "21-40", "41-60"],
    recallPlaceholder: "Enter a number from 0 to 60",
    recallCta: "Save",
    recallSavedTemplate: "Answer saved: {value}",
    recallError: "Enter a number between 0 and 60.",
    saveError: "Could not save. Please try again.",
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
    title: "Results",
    body: "You were not selected for the cash prize.",
    bodySecondary:
      "You are still entered in the draw for 2 tickets to SONAR 2027.",
    bodyFooter: "You can learn more about the study and its aggregated results at cotec.es, and about the winning code at the end of the festival.",
    shareLabel: "Invite on WhatsApp",
    shareMessageTemplate: "If you're at Sónar right now, try this activity: it takes 60 seconds and you can enter the draw for 2 tickets to Sónar 2027 and cash prizes of up to €60. Join here: {link}",
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
    braceletLabel: "Bracelet ID",
    braceletPlaceholder: "E.g. AB12CD34",
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
    braceletRequired: "Enter the bracelet ID",
    braceletMismatch:
      "Wrong bracelet, it does not match the one registered initially.",
    consentRequired:
      "Tick the privacy authorisation to continue",
    successEyebrow: "Request sent",
    successTitle: "You can still win",
    successBody: "Your Bizum request has been recorded successfully.",
    successDonationBody:
      "Your NGO donation request has been recorded successfully.",
    successSkipBody:
      "Your participation has already been recorded. You can continue without claiming the prize.",
    successSecondary:
      "You are also still entered in the draw for 2 VIP tickets.",
    successFooter: "You will be able to learn more about the study and its aggregated results at cotec.es, and about the winning code at the end of the festival.",
    successShareLabel: "Invite on WhatsApp",
    successShareMessageTemplate: "If you are at Sónar right now, try this: it takes 60 seconds and you can enter the draw for 2 VIP tickets for Sónar 2027 and cash prizes up to 60 €. Join here: {link}",
    skipMismatchLabel: "Continue without claiming prize",
    errorDefault: "Error sending request",
  },
  accessibility: {
    diceRollAria: "Roll die",
  },
  errors: {
    braceletNotFound: "Bracelet not found.",
    accessInvalid: "Invalid access.",
    sessionNotFound: "Session not found.",
    actionUnavailable: "This action is not available.",
    defaultMessage: "An unexpected error occurred.",
  },
});

const fr = withServerErrors({
  common: {
    appTitle: "SONAR 2026",
    languageSelectorAria: "Choisir la langue",
    loadingResume: "Récupération de la session",
    loadingPrepare: "Préparation de l'expérience",
    close: "Fermer",
    continueLabel: "Continuer",
    finalClosingMessage:
      "Merci beaucoup, vous avez terminé. Fermez le navigateur et profitez de l'expérience SONAR 2026.",
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
    braceletPlaceholder: "Ex : AB12CD34",
    moreInfoButton: "Plus d'information",
    ageCheckbox: "Je confirme avoir 18 ans ou plus",
    participationCheckbox: "J'ai lu les informations et j'accepte de participer",
    dataCheckbox: "J'ai lu et j'accepte le traitement des données",
    cta: "Commencer",
    footer: "",
    errors: {
      braceletRequired: "Entrez l'ID de votre bracelet.",
      consentsRequired: "Cochez les trois cases pour continuer.",
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
          "Vous saisirez le code de votre bracelet, verrez un lancer de dé, puis indiquerez le nombre obtenu. L'ensemble dure environ une minute.",
      },
      {
        title: "Paiement et incitations",
        body:
          "L'éligibilité au paiement est attribuée automatiquement. Si vous êtes sélectionné, le montant dépend du nombre que vous indiquerez et sera traité à la fin de l'activité.",
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
    title: "Merci de participer !",
    subtitle:
      "Rien qu’en participant, vous entrez dans un tirage au sort pour un billet SONAR 2027.",
    listLabel: "Instructions :",
    steps: [
      "Sur le premier écran, vous verrez les prix du jeu.",
      "Sur le suivant, vous trouverez un dé.",
      "Appuyez sur « Lancer ».",
      "Mémorisez le nombre.",
      "Ensuite, vous indiquerez le nombre.",
      "Et à la fin, vous verrez l’argent que vous avez gagné.",
    ],
    intro:
      "Sur le premier écran, vous verrez les prix du jeu, puis vous passerez au dé.",
    body:
      "La question suivante portera toujours sur le premier nombre.",
    odds: "",
    prizeTableLabel: "Instructions",
    cta: "Continuer",
  },
  comprehension: {
    eyebrow: "",
    title: "Table des prix :",
    body: "Chaque nombre correspond à un prix.",
    odds: "Une personne sur cent recevra le paiement réel (Bizum).",
    options: [
      "Indiquer quel nombre est sorti",
      "Choisir le prix que vous préférez",
      "Passer à l'écran suivant",
    ],
    errorEmpty: "",
    errorWrong: "",
    cta: "Continuer",
  },
  game: {
    title: "Lancez le dé",
    initialIntro: "Appuyez sur « Lancer » et mémorisez le premier nombre.",
    intro:
      "Quand vous avez bien le nombre en tête, continuez.",
    visibleResultLabel: "",
    firstResultTemplate: "Nombre obtenu : {value}",
    continueCta: "Continuer",
    firstRollCta: "Lancer",
    rerollCta: "Lancer",
    loading: "Chargement...",
    attemptsTemplate: "Lancer enregistré : {count}",
    errors: {
      noSession: "Aucune session active.",
      loadRoll: "Impossible de charger le lancer.",
      loadReport: "Impossible de continuer.",
    },
  },
  report: {
    title: "Quel nombre est sorti au premier lancer ?",
    body: "Sélectionnez le nombre qui est sorti au premier lancer.",
    errorSave: "Impossible d'enregistrer votre réponse.",
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
    controlBody: "Indiquez quel nombre est sorti.",
    socialMessageTemplate:
      "{count} participants sur {denominator} ont dit avoir obtenu un {target} avant vous.",
  },
  bonusDraw: {
    title: "Obtenez des chances supplémentaires pour le tirage SONAR 2027",
    intro: "Vous avez déjà 1 participation au tirage de 2 billets pour SONAR 2027 pour avoir pris part à l'activité.",
    prompt:
      "Quel nombre pensez-vous que les participants nous diront le plus souvent ?",
    baseTicket: "1 participation pour avoir pris part",
    predictionTicket: "1 supplémentaire si votre prédiction est correcte",
    recallTicket: "1 supplémentaire si vous vous souvenez du message",
    inviteTicket: "1 supplémentaire par personne du festival que vous invitez et qui participe",
    achievedLabel: "Obtenue",
    predictionAchieved: "Participation supplémentaire obtenue",
    selectedTemplate: "Prédiction enregistrée : {value}",
    recallPrompt:
      "Combien de personnes vous avons-nous dit avoir choisi le 6 parmi les 60 participants précédents ?",
    recallOptions: ["0-20", "21-40", "41-60"],
    recallPlaceholder: "Entrez un nombre de 0 à 60",
    recallCta: "Enregistrer",
    recallSavedTemplate: "Réponse enregistrée : {value}",
    recallError: "Entrez un nombre entre 0 et 60.",
    saveError: "Impossible d'enregistrer. Réessayez.",
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
    title: "Résultats",
    body: "Vous n'avez pas été sélectionné pour le prix en espèces.",
    bodySecondary:
      "Vous participez toujours au tirage de 2 billets pour SONAR 2027.",
    bodyFooter: "Vous pourrez en savoir plus sur l'étude et ses résultats agrégés sur cotec.es, ainsi que sur le code gagnant à la fin du festival.",
    shareLabel: "Inviter sur WhatsApp",
    shareMessageTemplate: "Si vous êtes au Sónar en ce moment, essayez cette activité : elle dure 60 secondes et vous permet de participer au tirage de 2 billets pour le Sónar 2027 ainsi qu'à des prix en argent jusqu'à 60 €. Participez ici : {link}",
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
    braceletLabel: "ID du bracelet",
    braceletPlaceholder: "Ex. AB12CD34",
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
    braceletRequired: "Saisissez l'ID du bracelet",
    braceletMismatch:
      "Bracelet incorrect, il ne correspond pas à celui enregistré au départ.",
    consentRequired:
      "Cochez l'autorisation de confidentialité pour continuer",
    successEyebrow: "Demande envoyée",
    successTitle: "Vous pouvez encore gagner",
    successBody: "Votre demande de Bizum a bien été enregistrée.",
    successDonationBody:
      "Votre demande de don à une ONG a bien été enregistrée.",
    successSkipBody:
      "Votre participation a déjà été enregistrée. Vous pouvez continuer sans réclamer le prix.",
    successSecondary:
      "Vous participez aussi toujours au tirage de 2 billets VIP.",
    successFooter: "Vous en saurez plus sur l'étude et ses résultats agrégés sur cotec.es, ainsi que sur le code gagnant à la fin du festival.",
    successShareLabel: "Inviter sur WhatsApp",
    successShareMessageTemplate: "Si vous êtes au Sónar en ce moment, essayez ceci : cela dure 60 secondes et vous pouvez participer au tirage de 2 billets VIP pour le Sónar 2027 ainsi qu'à des prix en argent jusqu'à 60 €. Participez ici : {link}",
    skipMismatchLabel: "Continuer sans réclamer le prix",
    errorDefault: "Erreur lors de l'envoi",
  },
  accessibility: {
    diceRollAria: "Lancer le dé",
  },
  errors: {
    braceletNotFound: "Bracelet introuvable.",
    accessInvalid: "Accès invalide.",
    sessionNotFound: "Session introuvable.",
    actionUnavailable: "Cette action n'est pas disponible.",
    defaultMessage: "Une erreur inattendue s'est produite.",
  },
});

const pt = withServerErrors({
  common: {
    appTitle: "SONAR 2026",
    languageSelectorAria: "Selecionar idioma",
    loadingResume: "A recuperar sessão",
    loadingPrepare: "A preparar experiência",
    close: "Fechar",
    continueLabel: "Continuar",
    finalClosingMessage:
      "Muito obrigado, terminaste. Fecha o navegador e desfruta da experiência SONAR 2026.",
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
    braceletPlaceholder: "Ex: AB12CD34",
    moreInfoButton: "Mais informação",
    ageCheckbox: "Confirmo que tenho 18 anos ou mais",
    participationCheckbox: "Li a informação e aceito participar",
    dataCheckbox: "Li e aceito o tratamento de dados",
    cta: "Começar",
    footer: "",
    errors: {
      braceletRequired: "Introduz o ID da tua pulseira.",
      consentsRequired: "Marca as três caixas para continuar.",
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
          "Vais introduzir o código da tua pulseira, ver uma tirada do dado e depois indicar que número saiu. O processo dura cerca de um minuto.",
      },
      {
        title: "Pagamento e incentivos",
        body:
          "A elegibilidade para pagamento é atribuída automaticamente. Se fores selecionado, o valor depende do número que indicares e é tratado no final da atividade.",
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
    title: "Obrigado por participares!",
    subtitle:
      "Só por participares, entras num sorteio para um bilhete do SONAR 2027.",
    listLabel: "Instruções:",
    steps: [
      "No primeiro ecrã vais ver os prémios do jogo.",
      "No seguinte, encontras um dado.",
      "Carrega em “Lançar”.",
      "Memoriza o número.",
      "Depois vais indicar o número.",
      "E no fim vais ver quanto dinheiro ganhaste.",
    ],
    intro:
      "No primeiro ecrã vais ver os prémios do jogo e depois passas ao dado.",
    body:
      "A pergunta seguinte refere-se sempre ao primeiro número.",
    odds: "",
    prizeTableLabel: "Instruções",
    cta: "Continuar",
  },
  comprehension: {
    eyebrow: "",
    title: "Tabela de prémios:",
    body: "Cada número está associado a um prémio.",
    odds: "Uma em cada cem pessoas receberá o dinheiro real (Bizum).",
    options: [
      "Indicar que número saiu",
      "Escolher o prémio que preferes",
      "Passar ao ecrã seguinte",
    ],
    errorEmpty: "",
    errorWrong: "",
    cta: "Continuar",
  },
  game: {
    title: "Lança o dado",
    initialIntro: "Carrega em “Lançar” e memoriza o primeiro número.",
    intro:
      "Quando tiveres claro o número, continua.",
    visibleResultLabel: "",
    firstResultTemplate: "Número obtido: {value}",
    continueCta: "Continuar",
    firstRollCta: "Lançar",
    rerollCta: "Lançar",
    loading: "A carregar...",
    attemptsTemplate: "Tirada registada: {count}",
    errors: {
      noSession: "Não há nenhuma sessão ativa.",
      loadRoll: "Não foi possível carregar a tirada.",
      loadReport: "Não foi possível continuar.",
    },
  },
  report: {
    title: "Que número te saiu na primeira tirada?",
    body: "Seleciona o número que te saiu na primeira tirada.",
    errorSave: "Não foi possível guardar a tua resposta.",
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
    controlBody: "Indica que número saiu.",
    socialMessageTemplate:
      "{count} de {denominator} participantes anteriores disseram que lhes saiu um {target}.",
  },
  bonusDraw: {
    title: "Consegue entradas extra para o sorteio de SONAR 2027",
    intro: "Já tens 1 participação no sorteio de 2 entradas para o SONAR 2027 por teres participado.",
    prompt:
      "Que número achas que as pessoas nos vão dizer mais vezes?",
    baseTicket: "1 participação por participar",
    predictionTicket: "1 extra se acertares na previsão",
    recallTicket: "1 extra se te lembrares da mensagem",
    inviteTicket: "1 extra por cada pessoa do festival que convidares e que participe",
    achievedLabel: "Conseguida",
    predictionAchieved: "Participação extra conseguida",
    selectedTemplate: "Previsão guardada: {value}",
    recallPrompt:
      "Quantas pessoas te dissemos que tinham escolhido o 6 entre 60 participantes anteriores?",
    recallOptions: ["0-20", "21-40", "41-60"],
    recallPlaceholder: "Escreve um número de 0 a 60",
    recallCta: "Guardar",
    recallSavedTemplate: "Resposta guardada: {value}",
    recallError: "Escreve um número entre 0 e 60.",
    saveError: "Não foi possível guardar. Tenta de novo.",
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
    title: "Resultados",
    body: "Não foste selecionado para o prémio em dinheiro.",
    bodySecondary:
      "Continuas a participar no sorteio de 2 entradas para o SONAR 2027.",
    bodyFooter: "Poderás saber mais sobre o estudo e os seus resultados agregados em cotec.es, e sobre o código vencedor no final do festival.",
    shareLabel: "Convidar por WhatsApp",
    shareMessageTemplate: "Se estás agora no Sónar, experimenta esta atividade: demora 60 segundos e podes entrar no sorteio de 2 entradas para o Sónar 2027 e ganhar prémios em dinheiro até 60 €. Participa aqui: {link}",
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
    braceletLabel: "ID da pulseira",
    braceletPlaceholder: "Ex.: AB12CD34",
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
    braceletRequired: "Introduz o ID da pulseira",
    braceletMismatch:
      "Pulseira errada, não coincide com a registada inicialmente.",
    consentRequired:
      "Marca a autorização de privacidade para continuar",
    successEyebrow: "Pedido enviado",
    successTitle: "Ainda podes ganhar",
    successBody: "O teu pedido de Bizum ficou registado corretamente.",
    successDonationBody:
      "O teu pedido de doação a uma ONG ficou registado corretamente.",
    successSkipBody:
      "A tua participação já ficou registada. Podes continuar sem reclamar o prémio.",
    successSecondary:
      "Além disso, continuas a participar no sorteio de 2 entradas VIP.",
    successFooter: "Saberás mais sobre o estudo e os seus resultados agregados em cotec.es, e sobre o código vencedor no final do festival.",
    successShareLabel: "Convidar por WhatsApp",
    successShareMessageTemplate: "Se estás agora no Sónar, experimenta isto: demora 60 segundos e podes entrar no sorteio de 2 entradas VIP para o Sónar 2027 e optar a prémios em dinheiro até 60 €. Participa aqui: {link}",
    skipMismatchLabel: "Continuar sem reclamar o prémio",
    errorDefault: "Erro ao enviar",
  },
  accessibility: {
    diceRollAria: "Lançar dado",
  },
  errors: {
    braceletNotFound: "Pulseira não encontrada.",
    accessInvalid: "Acesso inválido.",
    sessionNotFound: "Sessão não encontrada.",
    actionUnavailable: "Esta ação não está disponível.",
    defaultMessage: "Ocorreu um erro inesperado.",
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
    continueLabel: "Continua",
    finalClosingMessage:
      "Grazie mille, hai finito. Chiudi il browser e goditi l'esperienza SONAR 2026.",
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
    braceletPlaceholder: "Es: AB12CD34",
    moreInfoButton: "Piu informazioni",
    ageCheckbox: "Confermo di avere 18 anni o più",
    participationCheckbox: "Ho letto le informazioni e accetto di partecipare",
    dataCheckbox: "Ho letto e accetto il trattamento dei dati",
    cta: "Inizia",
    errors: {
      braceletRequired: "Inserisci l'ID del braccialetto.",
      consentsRequired: "Seleziona tutte e tre le caselle per continuare.",
      loading: "Accesso in corso...",
    },
  },
  infoModal: {
    title: "Informazioni",
    sections: [
      {
        title: "Che cos'e questa attivita",
        body:
          "Questa attivita fa parte di uno studio accademico sul processo decisionale in contesti digitali e culturali. E realizzata in collaborazione con un laboratorio di economia comportamentale.",
      },
      {
        title: "Che cosa farai",
        body:
          "Inserirai il codice del braccialetto, vedrai un lancio del dado e poi indicherai quale numero e uscito. Il processo dura circa un minuto.",
      },
      {
        title: "Pagamento e incentivi",
        body:
          "L'idoneita al pagamento viene assegnata automaticamente. Se vieni selezionato, l'importo dipendera dal numero che indichi e sara gestito al termine dell'attivita.",
      },
      {
        title: "Privacy e dati",
        body:
          "Il braccialetto viene usato solo per evitare partecipazioni duplicate. L'analisi viene svolta senza pubblicare identita personali e i risultati sono studiati in forma aggregata.",
      },
      {
        title: "Partecipazione volontaria",
        body:
          "La partecipazione e volontaria. Puoi interrompere l'attivita in qualsiasi momento prima di inviare la risposta finale. Una volta anonimizzati, i dati potranno essere usati per finalita scientifiche e pubblicazioni accademiche.",
      },
      {
        title: "Contatto",
        body:
          "Se hai domande sullo studio o sul pagamento, puoi rivolgerti al team presente allo stand o scrivere a lbl@uloyola.es.",
      },
    ],
  },
  instructions: {
    ...en.instructions,
    title: "Grazie per aver partecipato!",
    subtitle:
      "Solo per aver partecipato entri in un sorteggio per un biglietto SONAR 2027.",
    listLabel: "Istruzioni:",
    steps: [
      "Nella prima schermata vedrai i premi del gioco.",
      "In quella successiva troverai un dado.",
      "Premi “Lancia”.",
      "Memorizza il numero.",
      "Poi dovrai indicare il numero.",
      "E alla fine vedrai quanti soldi hai vinto.",
    ],
    intro:
      "Nella prima schermata vedrai i premi del gioco e poi passerai al dado.",
    body:
      "La domanda successiva riguarda sempre il primo numero.",
    odds: "",
    prizeTableLabel: "Istruzioni",
    cta: "Continua",
  },
  comprehension: {
    ...en.comprehension,
    eyebrow: "",
    title: "Tabella dei premi:",
    body: "Ogni numero corrisponde a un premio.",
    odds: "Una persona su cento riceverà il pagamento reale (Bizum).",
    options: [
      "Indicare quale numero è uscito",
      "Scegliere il premio che preferisci",
      "Passare alla schermata successiva",
    ],
    errorEmpty: "",
    errorWrong: "",
    cta: "Continua",
  },
  game: {
    ...en.game,
    title: "Lancia il dado",
    initialIntro: "Premi “Lancia” e memorizza il primo numero.",
    intro:
      "Quando hai chiaro il numero, continua.",
    firstResultTemplate: "Numero ottenuto: {value}",
    continueCta: "Continua",
    firstRollCta: "Lancia",
    rerollCta: "Lancia",
    loading: "Caricamento...",
    errors: {
      ...en.game.errors,
      noSession: "Non c'è una sessione attiva.",
      loadRoll: "Impossibile caricare il lancio.",
      loadReport: "Impossibile continuare.",
    },
  },
  report: {
    ...en.report,
    title: "Che cosa ti è uscito al primo lancio?",
    body: "Seleziona il numero che ti è uscito al primo lancio.",
    errorSave: "Impossibile salvare la tua risposta.",
  },
  treatment: {
    ...en.treatment,
    controlTitle: "La tua risposta e anonima",
    controlBody: "Indica quale numero e uscito.",
    socialMessageTemplate:
      "{count} partecipanti su {denominator} prima di te hanno detto di aver ottenuto un {target}.",
  },
  bonusDraw: {
    ...en.bonusDraw,
    title: "Ottieni possibilità extra per il sorteggio SONAR 2027",
    intro: "Hai già 1 partecipazione al sorteggio di 2 biglietti per SONAR 2027 per aver preso parte all'attività.",
    prompt: "Quale numero pensi che le persone ci diranno più spesso?",
    baseTicket: "1 partecipazione per aver partecipato",
    predictionTicket: "1 extra se indovini la previsione",
    recallTicket: "1 extra se ricordi il messaggio",
    inviteTicket: "1 extra per ogni persona del festival che inviti e che partecipa",
    achievedLabel: "Ottenuta",
    predictionAchieved: "Partecipazione extra ottenuta",
    selectedTemplate: "Previsione salvata: {value}",
    recallPrompt:
      "Quante persone ti abbiamo detto che avevano scelto il 6 tra i 60 partecipanti precedenti?",
    recallOptions: ["0-20", "21-40", "41-60"],
    recallPlaceholder: "Inserisci un numero da 0 a 60",
    recallCta: "Salva",
    recallSavedTemplate: "Risposta salvata: {value}",
    recallError: "Inserisci un numero tra 0 e 60.",
    saveError: "Impossibile salvare. Riprova.",
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
    title: "Risultati",
    body: "Non sei stato selezionato per il premio in denaro.",
    bodySecondary: "Continui a partecipare al sorteggio di 2 biglietti per SONAR 2027.",
    bodyFooter: "Potrai trovare maggiori informazioni sullo studio e sui suoi risultati aggregati su cotec.es, e sul codice vincente alla fine del festival.",
    shareLabel: "Invita via WhatsApp",
    shareMessageTemplate:
      "Se sei al Sónar in questo momento, prova questa attività: dura 60 secondi e puoi partecipare al sorteggio di 2 biglietti per il Sónar 2027 e concorrere a premi in denaro fino a 60 euro. Partecipa qui: {link}",
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
    braceletLabel: "ID del braccialetto",
    braceletPlaceholder: "Es: AB12CD34",
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
    braceletRequired: "Inserisci l'ID del braccialetto",
    braceletMismatch:
      "Braccialetto errato, non coincide con quello registrato inizialmente.",
    consentRequired:
      "Segna l'autorizzazione privacy per continuare",
    successEyebrow: "Richiesta inviata",
    successTitle: "Puoi ancora vincere",
    successBody: "La tua richiesta di Bizum e stata registrata correttamente.",
    successDonationBody:
      "La tua richiesta di donazione a una ONG e stata registrata correttamente.",
    successSkipBody:
      "La tua partecipazione e gia stata registrata. Puoi continuare senza reclamare il premio.",
    successSecondary:
      "Inoltre continui a partecipare al sorteggio di 2 biglietti VIP.",
    successFooter:
      "Saprai di piu sullo studio e sui suoi risultati aggregati su cotec.es, e sul codice vincente alla fine del festival.",
    successShareLabel: "Invita via WhatsApp",
    successShareMessageTemplate:
      "Se sei al Sónar in questo momento, prova questo: ti richiede 60 secondi e puoi entrare nel sorteggio di 2 biglietti VIP per il Sónar 2027 e concorrere a premi in denaro fino a 60 euro. Partecipa qui: {link}",
    skipMismatchLabel: "Continua senza reclamare il premio",
    errorDefault: "Errore durante l'invio",
  },
  accessibility: {
    ...en.accessibility,
    diceRollAria: "Lancia il dado",
  },
  errors: {
    braceletNotFound: "Braccialetto non trovato.",
    accessInvalid: "Accesso non valido.",
    sessionNotFound: "Sessione non trovata.",
    actionUnavailable: "Questa azione non è disponibile.",
    defaultMessage: "Si è verificato un errore imprevisto.",
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

