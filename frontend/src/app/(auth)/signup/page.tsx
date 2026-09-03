import type { Metadata } from "next";
import { SignupForm } from "./SignupForm";

export const metadata: Metadata = { title: "Create account — LookMaxx" };

export default function SignupPage() {
  return <SignupForm />;
}
