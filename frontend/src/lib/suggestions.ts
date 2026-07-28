import { Briefcase, Building2, Gavel, Scale, Users } from "lucide-react";

/**
 * Suggestion chip content, one per law actually in this project's
 * indexed corpus.
 *
 * WHY THESE FIVE SPECIFIC QUESTIONS, NOT GENERIC CATEGORY LABELS
 * -------------------------------------------------------------------------
 * The design brief's example chips (Constitution, Traffic Rules, Tax
 * Code, Administrative Code, ...) don't match what this project actually
 * has indexed (see README.md's corpus table — five specific codes, not
 * those). A chip that fills the search with a question the backend can't
 * actually answer would make a new user's very first interaction a
 * "not found" response — a bad first impression for something meant to
 * demonstrate the system working. Each `query` below is copied directly
 * from `tests/evaluation/golden_dataset.py` (Milestone 20 of the
 * Streamlit build) — a hand-verified query, checked against the real
 * source text, that this retrieval pipeline is confirmed to answer
 * correctly (found within the top-5 reranked results in that test).
 */
export interface Suggestion {
  icon: typeof Briefcase;
  label: string;
  query: string;
}

export const SUGGESTIONS: Suggestion[] = [
  {
    icon: Briefcase,
    label: "Mehnat kodeksi",
    query:
      "Ish beruvchi mehnat shartnomasini bekor qilish niyati haqida xodimni necha muddatda ogohlantirishi kerak?",
  },
  {
    icon: Gavel,
    label: "Jinoyat kodeksi",
    query: "Jinoyat sodir etgan shaxs necha yoshga toʻlgan boʻlishi kerak javobgarlikka tortilishi uchun?",
  },
  {
    icon: Scale,
    label: "Fuqarolik kodeksi",
    query: "Fuqaroning toʻla muomala layoqati necha yoshda vujudga keladi?",
  },
  {
    icon: Users,
    label: "Fuqarolik protsessual kodeksi",
    query: "Nikohni bekor qilish toʻgʻrisidagi ish bilan birga qanday nizolarni koʻrib chiqish mumkin emas?",
  },
  {
    icon: Building2,
    label: "Iqtisodiy protsessual kodeksi",
    query: "Iqtisodiy sudda qanday ishlar korporativ nizolar deb hisoblanadi?",
  },
];
