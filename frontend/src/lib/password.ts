// Shared password rules + live strength scoring (§7, §13).
//
// These mirror the backend `validate_password_strength` exactly, so the client
// rejects a weak password before it ever reaches the API and the signup/reset
// forms can render a live strength meter whose verdict never disagrees with the
// server.

import { z } from "zod";

const COMMON_PASSWORDS = new Set([
  "password", "password1", "password123", "12345678", "123456789", "1234567890",
  "qwerty", "qwerty123", "qwertyuiop", "letmein", "lookmaxx", "lookmaxxing",
  "iloveyou", "admin123", "welcome1", "monkey123", "football", "baseball",
  "dragon123", "sunshine", "princess", "trustno1", "abc123", "11111111",
  "00000000", "aaaaaaaa", "changeme", "master123", "superman1", "batman123",
]);

function classCount(pw: string): number {
  let classes = 0;
  if (/[a-z]/.test(pw)) classes += 1;
  if (/[A-Z]/.test(pw)) classes += 1;
  if (/\d/.test(pw)) classes += 1;
  if (/[^A-Za-z0-9]/.test(pw)) classes += 1;
  return classes;
}

/** Zod schema shared by signup and reset-password forms. */
export const passwordSchema = z
  .string()
  .min(1, "Password is required.")
  .min(8, "Password must be at least 8 characters.")
  .max(128, "Password is too long.")
  .refine((v) => !COMMON_PASSWORDS.has(v.toLowerCase()), "That password is too common. Choose something more unique.")
  .refine((v) => classCount(v) >= 2, "Use at least two of: lowercase, uppercase, numbers, or symbols.");

export interface PasswordStrength {
  /** 0 (empty) → 4 (strongest). */
  score: 0 | 1 | 2 | 3 | 4;
  label: string;
  hint: string;
}

/** Live strength verdict for the meter. Never throws. */
export function passwordStrength(pw: string): PasswordStrength {
  if (!pw) return { score: 0, label: "", hint: "Use at least 8 characters." };
  if (COMMON_PASSWORDS.has(pw.toLowerCase())) {
    return { score: 1, label: "Too common", hint: "Choose something more unique." };
  }
  if (pw.length < 8) {
    return { score: 1, label: "Too short", hint: "Use at least 8 characters." };
  }

  const classes = classCount(pw);
  const long = pw.length >= 12;

  if (classes < 2) {
    return { score: 1, label: "Weak", hint: "Add numbers, capitals, or symbols." };
  }
  if (classes >= 3 && long) {
    return { score: 4, label: "Strong", hint: "Great password." };
  }
  if (classes >= 3) {
    return { score: 3, label: "Good", hint: "Add length for extra strength." };
  }
  return { score: 2, label: "Fair", hint: "Add another character type." };
}
