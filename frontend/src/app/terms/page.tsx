import Link from "next/link";

export default function TermsPage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-16 text-ink">
      <h1 className="font-display text-3xl font-bold">Terms of Service</h1>
      <p className="mt-4 text-muted">
        The full terms are maintained in the repository at{" "}
        <code className="text-ink">docs/TERMS_OF_SERVICE.md</code> and are
        pending review by a qualified lawyer before public launch.
      </p>
      <div className="mt-6 space-y-3 rounded-card card-border p-5 text-sm text-muted">
        <p>
          <strong className="text-ink">Age requirement.</strong> LookMaxx is for
          ages 13 and up. By creating an account you confirm you meet the age
          requirement.
        </p>
        <p>
          <strong className="text-ink">Not medical advice.</strong> Scores and
          recommendations are for personal improvement and entertainment — they
          are not a substitute for professional medical or dermatological
          advice.
        </p>
      </div>
      <p className="mt-8 text-sm">
        <Link href="/" className="text-gold hover:text-gold-bright">
          ← Back home
        </Link>
      </p>
    </div>
  );
}
