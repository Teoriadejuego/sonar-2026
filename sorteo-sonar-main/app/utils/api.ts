const envUrl = import.meta.env.API_BASE_URL || import.meta.env.VITE_API_URL;
const API_BASE_URL = envUrl
  ? envUrl.replace(/\/$/, "")
  : "http://127.0.0.1:8000";

export type PublicConfig = {
  schema_version: string;
  experiment_version: string;
  current_phase: string;
  phase_transition_threshold: number;
  max_attempts: number;
  participant_limit: number;
  window_size: number;
  prize_eur: Record<string, number>;
  treatments: string[];
  seed_initial_counts: Record<string, number>;
  collapse_consecutive_claims: number;
  treatment_version: string;
  allocation_version: string;
  deployment_context: string;
  site_code: string;
  campaign_code: string;
  environment_label: string;
  experiment_control: {
    status: "active" | "paused";
    paused: boolean;
    paused_at: string | null;
  };
  support: {
    winner_whatsapp_phone: string;
  };
  copy: {
    landing: {
      eyebrow: string;
      title: string;
      subtitle: string;
      intro: string;
      bracelet_label: string;
      bracelet_placeholder: string;
      panel_links: {
        study: string;
        data_protection: string;
        withdrawal: string;
        contact: string;
      };
      age_checkbox: string;
      participation_checkbox: string;
      data_checkbox: string;
      cta: string;
      footer: string;
    };
    info_panels: {
      close_label: string;
      study: {
        title: string;
        sections: Array<{
          title: string;
          body: string;
        }>;
      };
      data_protection: {
        title: string;
        sections: Array<{
          title: string;
          body: string;
        }>;
      };
      withdrawal: {
        title: string;
        sections: Array<{
          title: string;
          body: string;
        }>;
      };
      contact: {
        title: string;
        sections: Array<{
          title: string;
          body: string;
        }>;
      };
    };
    consent: {
      modal_title: string;
      close_label: string;
      sections: Array<{
        title: string;
        body: string;
      }>;
    };
    instructions: {
      eyebrow: string;
      title: string;
      intro: string;
      body: string;
      cta: string;
    };
    comprehension: {
      eyebrow: string;
      title: string;
      options: string[];
      error_empty: string;
      error_wrong: string;
      cta: string;
    };
    messages: {
      control: string;
      social_template: string;
    };
    winner: {
      eyebrow: string;
      title: string;
      body: string;
      code_label: string;
      help: string;
      whatsapp_label: string;
      whatsapp_message_template: string;
    };
    loser: {
      eyebrow: string;
      title: string;
      body: string;
      body_secondary: string;
      body_footer: string;
      share_label: string;
      share_message_template: string;
    };
  };
};

export const DEFAULT_PUBLIC_CONFIG: PublicConfig = {
  schema_version: "sonar-2026-v6",
  experiment_version: "sonar-2026-field-v2",
  current_phase: "phase_1_main",
  phase_transition_threshold: 6000,
  max_attempts: 10,
  participant_limit: 250,
  window_size: 100,
  prize_eur: { "1": 10, "2": 20, "3": 30, "4": 40, "5": 50, "6": 60 },
  treatments: ["control", "seed_17", "seed_83"],
  seed_initial_counts: {
    seed_17: 17,
    seed_83: 83,
  },
  collapse_consecutive_claims: 10,
  treatment_version: "phase_1_six_norms_v1",
  allocation_version: "phase_1_10_45_45_v1",
  deployment_context: "main_event",
  site_code: "SONAR2026",
  campaign_code: "festival_main",
  environment_label: "local",
  experiment_control: {
    status: "active",
    paused: false,
    paused_at: null,
  },
  support: {
    winner_whatsapp_phone: "0034693494561",
  },
  copy: {
    landing: {
      eyebrow: "Participa en el estudio",
      title:
        "Participa en 1 minuto y gana una entrada para dos personas para Sonar 2027, y hasta 60 EUR al momento.",
      subtitle: "",
      intro:
        "Investigacion universitaria, participacion voluntaria, menos de 90 segundos y solo para mayores de 18 años.",
      bracelet_label: "ID de tu pulsera",
      bracelet_placeholder: "Ej: 10000001",
      panel_links: {
        study: "Informacion del estudio",
        data_protection: "Proteccion de datos",
        withdrawal: "Retirada",
        contact: "Contacto",
      },
      age_checkbox: "Confirmo que tengo 18 años o mas",
      participation_checkbox:
        "He leido la informacion basica y acepto participar",
      data_checkbox: "He leido y acepto el tratamiento de datos",
      cta: "Comenzar",
      footer: "1 de cada 100 participantes recibe el pago.",
    },
    info_panels: {
      close_label: "Cerrar",
      study: {
        title: "Informacion del estudio",
        sections: [
          {
            title: "Finalidad",
            body: "Esta actividad forma parte de una investigacion universitaria sobre toma de decisiones en entornos digitales y culturales, diseñada para su analisis cientifico posterior.",
          },
        ],
      },
      data_protection: {
        title: "Proteccion de datos",
        sections: [
          {
            title: "Datos utilizados",
            body: "El codigo de pulsera se utiliza para evitar participaciones duplicadas y para gestionar el incentivo. La informacion se analiza sin publicar identidades personales.",
          },
        ],
      },
      withdrawal: {
        title: "Retirada",
        sections: [
          {
            title: "Antes de terminar",
            body: "Puedes dejar la actividad en cualquier momento antes de enviar tu respuesta final sin ninguna consecuencia.",
          },
        ],
      },
      contact: {
        title: "Contacto",
        sections: [
          {
            title: "Equipo",
            body: "Puedes consultar cualquier duda con el equipo del experimento presente en el recinto o escribir a lbl@uloyola.es.",
          },
        ],
      },
    },
    consent: {
      modal_title: "Hoja informativa y consentimiento",
      close_label: "Cerrar",
      sections: [
        {
          title: "Que es esta actividad",
          body: "Esta actividad forma parte de un estudio academico sobre toma de decisiones en contextos digitales y culturales.",
        },
      ],
    },
    instructions: {
      eyebrow: "Como funciona",
      title: "Como funciona",
      intro:
        "Lanza un dado. Despues te preguntaremos cual fue el primer numero que te salio.",
      body:
        "Segun el numero que nos indiques, podras ganar el premio que aparece en la tabla.",
      cta: "Continuar",
    },
    comprehension: {
      eyebrow: "Antes de seguir",
      title: "Que numero es el que nos tienes que decir",
      options: ["La primera tirada", "La ultima tirada", "La mas alta que vea"],
      error_empty: "Elige una opcion para seguir.",
      error_wrong: "Recuerda: cuenta la primera tirada.",
      cta: "Seguir",
    },
    messages: {
      control:
        "Tu respuesta se registrara de forma anonima. Indica el numero de tu primera tirada.",
      social_template:
        "{count} de los {denominator} participantes anteriores reportaron un {target}.",
    },
    winner: {
      eyebrow: "Has sido seleccionado",
      title: "Pago confirmado",
      body:
        "Tu respuesta ha quedado registrada y has sido seleccionado para el pago.",
      code_label: "Codigo de cobro",
      help:
        "Usa este codigo para validar tu premio y enviar la solicitud de cobro por WhatsApp.",
      whatsapp_label: "Cobrar por WhatsApp",
      whatsapp_message_template:
        "he recibido un premio de {amount} euros, con el codigo {code}, quiero cobrarlo recibiendo un bizum en este telefono, si prefieres donar tu premio a una ong, tras este mensaje escribe ONG.",
    },
    loser: {
      eyebrow: "Gracias por participar",
      title: "Aun puedes ganar",
      body:
        "No has sido seleccionado para el pago en esta ocasion, pero aun queda un sorteo de 2 entradas VIP para el año que viene.",
      body_secondary:
        "Aumenta tus posibilidades invitando a otras personas a participar desde tu enlace.",
      body_footer:
        "El ganador se publicara en nuestra web al finalizar el festival. Guarda tu pulsera y, si te toca, nos vemos el año que viene.",
      share_label: "Invitar por WhatsApp",
      share_message_template:
        "Prueba este reto de Sonar 2026 y participa en el sorteo final: {link}",
    },
  },
};

export type SessionState =
  | "assigned"
  | "in_game"
  | "report_ready"
  | "completed_win"
  | "completed_no_win";

export type ScreenCursor =
  | "landing"
  | "instructions"
  | "comprehension"
  | "game"
  | "report"
  | "exit";

export type ThrowSummary = {
  attempt_index: number;
  result_value: number;
  reaction_ms?: number | null;
  delivered_at: string;
};

export type ReportSnapshot = {
  treatment_key: string;
  count_target: number | null;
  denominator: number | null;
  target_value: number | null;
  window_version: number | null;
  message: string;
  message_version: string | null;
  is_control: boolean;
};

export type ClaimSummary = {
  reported_value: number;
  true_first_result: number;
  is_honest: boolean;
  matches_last_seen: boolean;
  matches_any_seen: boolean;
  submitted_at: string;
};

export type PaymentSummary = {
  eligible: boolean;
  amount_cents: number;
  amount_eur: number;
  status: string;
  reference_code: string | null;
};

export type ClientContextSummary = {
  browser_family: string | null;
  browser_version: string | null;
  os_family: string | null;
  os_version: string | null;
  device_type: string | null;
  platform: string | null;
  language_browser: string | null;
  language_app_selected: string | null;
  screen_width: number | null;
  screen_height: number | null;
  viewport_width: number | null;
  viewport_height: number | null;
  device_pixel_ratio: number | null;
  orientation: string | null;
  touch_capable: boolean | null;
  hardware_concurrency: number | null;
  max_touch_points: number | null;
  color_scheme_preference: string | null;
  online_status: string | null;
  connection_type: string | null;
  estimated_downlink: number | null;
  estimated_rtt: number | null;
  timezone_offset_minutes: number | null;
};

export type SessionMetricsSummary = {
  resume_count: number;
  refresh_count: number;
  blur_count: number;
  network_error_count: number;
  retry_count: number;
  click_count_total: number;
  screen_changes_count: number;
  language_change_count: number;
  telemetry_event_count: number;
  max_event_sequence_number: number;
};

export type ConsentRecordSummary = {
  language_at_access: string | null;
  landing_visible_ms: number | null;
  info_panels_opened: string[];
  info_panel_durations_ms: Record<string, number>;
  checkbox_order: string[];
  checkbox_timestamps_ms: Record<string, number>;
  continue_blocked_count: number;
};

export type SnapshotRecordSummary = {
  language_used: string | null;
  displayed_message_text: string | null;
  control_message_text: string | null;
  final_message_text: string | null;
  payout_reference_shown: string | null;
  payout_phone_shown?: string | null;
  first_result_value?: number | null;
  last_seen_value?: number | null;
  all_values_seen?: number[];
  rerolls_visible?: number[];
  final_state_shown?: string | null;
};

export type SessionPayload = {
  session_id: string;
  state: SessionState;
  screen: ScreenCursor;
  experiment_version: string;
  experiment_phase: string;
  phase_version: string;
  phase_activation_status: string;
  ui_version: string;
  consent_version: string;
  treatment_version: string;
  treatment_text_version: string;
  allocation_version: string;
  deck_version: string;
  payment_version: string;
  telemetry_version: string;
  lexicon_version: string;
  treatment_key: string;
  treatment_family: string;
  norm_target_value: number | null;
  language_at_access: string | null;
  language_at_claim: string | null;
  language_changed_during_session: boolean;
  deployment_context: string;
  site_code: string;
  campaign_code: string;
  environment_label: string;
  bracelet_status: "active" | "completed";
  consent: {
    accepted: boolean;
    age_confirmed: boolean;
    info_accepted: boolean;
    data_accepted: boolean;
    accepted_at: string | null;
  };
  referral_code: string;
  invited_by_session_id: string | null;
  invited_by_referral_code: string | null;
  referral_source: string | null;
  referral_medium?: string | null;
  referral_campaign?: string | null;
  referral_link_id?: string | null;
  referral_landing_path: string | null;
  referral_arrived_at?: string | null;
  position_index: number;
  root_sequence: number;
  selected_for_payment: boolean;
  max_attempts: number;
  first_result_value: number | null;
  last_seen_value: number | null;
  max_seen_value: number | null;
  reroll_count: number;
  is_valid_completed: boolean;
  valid_completed_at: string | null;
  report_snapshot: ReportSnapshot | null;
  throws: ThrowSummary[];
  claim: ClaimSummary | null;
  payment: PaymentSummary;
  quality_flags: string[];
  antifraud_flags: string[];
  client_context?: ClientContextSummary | null;
  session_metrics?: SessionMetricsSummary | null;
  consent_record?: ConsentRecordSummary | null;
  snapshot_record?: SnapshotRecordSummary | null;
  screen_metrics?: Record<
    string,
    {
      entries: number;
      duration_total_ms: number;
      visible_ms: number;
      hidden_ms: number;
      blur_ms: number;
      click_count: number;
      primary_click_count: number;
      secondary_click_count: number;
    }
  > | null;
  series: {
    experiment_phase: string;
    treatment_key: string;
    treatment_family: string;
    norm_target_value: number | null;
    completed_count: number;
    visible_count_target: number;
    actual_count_target: number;
    visible_window_version: number;
    actual_window_version: number;
  };
};

export type SessionEnvelope = {
  created_now: boolean;
  session: SessionPayload;
};

export type RollResponse = {
  attempt: {
    attempt_index: number;
    result_value: number;
    is_first_roll: boolean;
    remaining_attempts: number;
  };
  session: SessionPayload;
};

export type TelemetryEventRequest = {
  event_type: string;
  event_name: string;
  screen_name?: string;
  client_ts?: number;
  event_sequence_number?: number;
  timezone_offset_minutes?: number;
  duration_ms?: number;
  value?: number;
  app_language?: string;
  browser_language?: string;
  spell_id?: string;
  interaction_target?: string;
  interaction_role?: string;
  cta_kind?: string;
  endpoint_name?: string;
  request_method?: string;
  status_code?: number;
  latency_ms?: number;
  attempt_number?: number;
  is_retry?: boolean;
  error_name?: string;
  network_status?: string;
  visibility_state?: string;
  payload?: Record<string, unknown>;
  client_context?: ClientContext;
};

export type ClientContext = {
  user_agent_raw?: string;
  browser_family?: string;
  browser_version?: string;
  os_family?: string;
  os_version?: string;
  device_type?: string;
  platform?: string;
  language_browser?: string;
  language_app_selected?: string;
  screen_width?: number;
  screen_height?: number;
  viewport_width?: number;
  viewport_height?: number;
  device_pixel_ratio?: number;
  orientation?: string;
  touch_capable?: boolean;
  hardware_concurrency?: number;
  max_touch_points?: number;
  color_scheme_preference?: string;
  online_status?: string;
  connection_type?: string;
  estimated_downlink?: number;
  estimated_rtt?: number;
  timezone_offset_minutes?: number;
};

export type DisplaySnapshotRequest = {
  screen_name: string;
  language?: string;
  treatment_message_text?: string;
  control_message_text?: string;
  final_message_text?: string;
  payout_reference_shown?: string;
  payout_phone_shown?: string;
  final_amount_eur?: number;
  rerolls_visible?: number[];
};

export type PaymentLookupResponse = {
  valid: boolean;
  status: string;
  amount_eur: number;
  code: string;
  can_submit: boolean;
  donation_available: boolean;
  experiment_phase: string;
};

export type PaymentSubmitResponse = {
  ok: boolean;
  status: string;
  amount_eur: number;
  requested_phone: string;
  donation_requested: boolean;
};

export type InterestSignupResponse = {
  ok: boolean;
  stored: boolean;
};

export class UserNotFoundError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "UserNotFoundError";
  }
}

async function parseError(response: Response, fallback: string) {
  const error = await response.json().catch(() => ({ detail: fallback }));
  if (typeof error.detail === "string") {
    return error.detail;
  }
  if (error.detail?.message) {
    return error.detail.message as string;
  }
  return fallback;
}

type RequestTelemetryReporter = (event: TelemetryEventRequest) => void;
let apiTelemetryReporter: RequestTelemetryReporter | null = null;

export function setApiTelemetryReporter(
  reporter: RequestTelemetryReporter | null,
) {
  apiTelemetryReporter = reporter;
}

async function requestJson<T>(input: string, init?: RequestInit): Promise<T> {
  const startedAt = Date.now();
  const method = init?.method ?? "GET";
  const telemetryAllowed = input !== "/v1/telemetry/batch";
  try {
    const response = await fetch(`${API_BASE_URL}${input}`, init);
    if (telemetryAllowed && apiTelemetryReporter) {
      apiTelemetryReporter({
        event_type: "network",
        event_name: response.ok ? "api_success" : "api_error",
        endpoint_name: input,
        request_method: method,
        status_code: response.status,
        latency_ms: Date.now() - startedAt,
        network_status:
          typeof navigator !== "undefined" && navigator.onLine
            ? "online"
            : "offline",
      });
    }
  if (!response.ok) {
    if (response.status === 404) {
      throw new UserNotFoundError(await parseError(response, "No encontrado"));
    }
    throw new Error(await parseError(response, "Error inesperado"));
  }
  return response.json() as Promise<T>;
  } catch (error) {
    if (telemetryAllowed && apiTelemetryReporter) {
      apiTelemetryReporter({
        event_type: "network",
        event_name: "api_exception",
        endpoint_name: input,
        request_method: method,
        latency_ms: Date.now() - startedAt,
        network_status:
          typeof navigator !== "undefined" && navigator.onLine
            ? "online"
            : "offline",
        error_name: error instanceof Error ? error.name : "RequestError",
        payload: {
          message: error instanceof Error ? error.message : "Unexpected request error",
        },
      });
    }
    throw error;
  }
}

export async function accessSession(
  braceletId: string,
  consentAccepted: boolean,
  clientInstallationId: string,
  language?: string | null,
  landingVisibleMs?: number | null,
  infoPanelsOpened?: string[],
  infoPanelDurationsMs?: Record<string, number>,
  referralCode?: string | null,
  referralSource?: string | null,
  referralMedium?: string | null,
  referralCampaign?: string | null,
  referralLinkId?: string | null,
  referralPath?: string | null,
  consentAgeConfirmed?: boolean,
  consentInfoAccepted?: boolean,
  consentDataAccepted?: boolean,
  consentCheckboxOrder?: string[],
  consentCheckboxTimestampsMs?: Record<string, number>,
  consentContinueBlockedCount?: number,
  clientContext?: ClientContext,
): Promise<SessionEnvelope> {
  return requestJson<SessionEnvelope>("/v1/session/access", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      bracelet_id: braceletId,
      consent_accepted: consentAccepted,
      consent_age_confirmed: consentAgeConfirmed ?? false,
      consent_info_accepted: consentInfoAccepted ?? false,
      consent_data_accepted: consentDataAccepted ?? false,
      language,
      landing_visible_ms: landingVisibleMs,
      info_panels_opened: infoPanelsOpened ?? [],
      info_panel_durations_ms: infoPanelDurationsMs ?? {},
      client_installation_id: clientInstallationId,
      referral_code: referralCode,
      referral_source: referralSource,
      referral_medium: referralMedium,
      referral_campaign: referralCampaign,
      referral_link_id: referralLinkId,
      referral_path: referralPath,
      consent_checkbox_order: consentCheckboxOrder ?? [],
      consent_checkbox_timestamps_ms: consentCheckboxTimestampsMs ?? {},
      consent_continue_blocked_count: consentContinueBlockedCount ?? 0,
      client_context: clientContext ?? null,
    }),
  });
}

export async function resumeSession(
  sessionId: string,
): Promise<SessionEnvelope> {
  return requestJson<SessionEnvelope>(`/v1/session/${sessionId}/resume`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
}

export async function updateScreenCursor(
  sessionId: string,
  screen: ScreenCursor,
): Promise<{ session: SessionPayload }> {
  return requestJson<{ session: SessionPayload }>(
    `/v1/session/${sessionId}/screen`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ screen }),
    },
  );
}

export async function rollSession(
  sessionId: string,
  attemptIndex: number,
  reactionMs: number | undefined,
  idempotencyKey: string,
): Promise<RollResponse> {
  return requestJson<RollResponse>(`/v1/session/${sessionId}/roll`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      attempt_index: attemptIndex,
      reaction_ms: reactionMs,
      idempotency_key: idempotencyKey,
    }),
  });
}

export async function prepareReport(
  sessionId: string,
  idempotencyKey: string,
): Promise<{ session: SessionPayload }> {
  return requestJson<{ session: SessionPayload }>(
    `/v1/session/${sessionId}/prepare-report`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ idempotency_key: idempotencyKey }),
    },
  );
}

export async function submitReport(
  sessionId: string,
  reportedValue: number,
  reactionMs: number | undefined,
  idempotencyKey: string,
  language?: string,
): Promise<{ session: SessionPayload }> {
  return requestJson<{ session: SessionPayload }>(
    `/v1/session/${sessionId}/submit-report`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        reported_value: reportedValue,
        reaction_ms: reactionMs,
        idempotency_key: idempotencyKey,
        language,
      }),
    },
  );
}

export async function captureDisplaySnapshot(
  sessionId: string,
  payload: DisplaySnapshotRequest,
): Promise<{ ok: boolean }> {
  return requestJson<{ ok: boolean }>(
    `/v1/session/${sessionId}/display-snapshot`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
}

export async function paymentLookup(
  code: string,
): Promise<PaymentLookupResponse> {
  return requestJson<PaymentLookupResponse>("/v1/payment/lookup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });
}

export async function paymentSubmit(
  code: string,
  phone: string,
  language?: string,
  donationRequested?: boolean,
  messageText?: string,
): Promise<PaymentSubmitResponse> {
  return requestJson<PaymentSubmitResponse>("/v1/payment/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      code,
      phone,
      language,
      donation_requested: donationRequested ?? false,
      message_text: messageText,
      }),
    });
}

export async function submitInterestSignup(
  email: string,
  language?: string,
): Promise<InterestSignupResponse> {
  return requestJson<InterestSignupResponse>("/v1/interest-signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      language,
    }),
  });
}

export async function postTelemetryBatch(
  sessionId: string,
  events: TelemetryEventRequest[],
): Promise<{ accepted_count: number }> {
  return requestJson<{ accepted_count: number }>("/v1/telemetry/batch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      events,
    }),
  });
}

export async function fetchPublicConfig(): Promise<PublicConfig> {
  return requestJson<PublicConfig>("/v1/config", {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
}
