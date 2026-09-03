import Link from "next/link";

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-16 text-ink">
      <h1 className="font-display text-3xl font-bold">Privacy Policy</h1>
      <p className="mt-4 text-muted">
        The full privacy policy is maintained in the repository at{" "}
        <code className="text-ink">docs/PRIVACY_POLICY.md</code> and is pending
        review by a qualified lawyer before public launch.
      </p>
      <div className="mt-6 space-y-3 rounded-card card-border p-5 text-sm text-muted">
        <p>
          <strong className="text-ink">Photos are biometric data.</strong> Your
          face photo is used only to compute numeric scores and build your plan.
          It is never sold, never shared with advertisers, and never sent to
          third-party AI services in identifiable form.
        </p>
        <p>
          You can export or permanently delete your account and all photos at
          any time from Settings — deletion also removes images from our storage
          provider.
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
