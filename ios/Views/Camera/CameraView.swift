import SwiftUI

/// Screen 2 — Camera / Upload.
///
/// Psychology: Anticipation.
/// Photo upload should feel like the start of an adventure, not a chore.
struct CameraView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var viewModel = PhotoViewModel()
    @State private var showPhotoPicker = false
    @State private var navigateToPreview = false
    @State private var pulse = false

    var body: some View {
        NavigationStack {
            ZStack {
                LXColor.black.ignoresSafeArea()

                VStack(spacing: 32) {
                    Spacer()

                    Text("Take or Upload\nYour Photo")
                        .lxH2()
                        .foregroundColor(LXColor.white)
                        .multilineTextAlignment(.center)

                    // Camera circle
                    Button(action: { showPhotoPicker = true }) {
                        ZStack {
                            Circle()
                                .strokeBorder(LXColor.gold, lineWidth: 3)
                                .frame(width: 180, height: 180)
                                .scaleEffect(pulse ? 1.08 : 1.0)
                                .animation(LXAnimation.pulse, value: pulse)

                            Circle()
                                .fill(LXColor.deepNavy)
                                .frame(width: 160, height: 160)

                            VStack(spacing: 8) {
                                Image(systemName: "camera.fill")
                                    .font(.system(size: 40))
                                    .foregroundColor(LXColor.gold)
                                Text("Tap to take photo")
                                    .lxCaption()
                                    .foregroundColor(LXColor.white.opacity(0.6))
                            }
                        }
                    }
                    .onAppear { pulse = true }

                    Text("OR")
                        .lxCaption()
                        .foregroundColor(LXColor.white.opacity(0.3))

                    // Gallery button
                    Button(action: { showPhotoPicker = true }) {
                        HStack(spacing: 8) {
                            Image(systemName: "photo.on.rectangle")
                            Text("Choose from Gallery")
                        }
                        .lxBody()
                        .frame(maxWidth: .infinity)
                        .frame(height: LXConstants.buttonHeight)
                        .background(LXColor.deepNavy)
                        .foregroundColor(LXColor.white)
                        .cornerRadius(LXConstants.cornerRadius)
                    }
                    .padding(.horizontal, LXConstants.standardPadding)

                    Text("For best results, use a well-lit photo")
                        .lxCaption()
                        .foregroundColor(LXColor.white.opacity(0.5))

                    Spacer()
                }
            }
            .sheet(isPresented: $showPhotoPicker) {
                PHPickerSwiftUI(selectedImage: $viewModel.selectedImage) { _ in
                    navigateToPreview = true
                }
            }
            .navigationDestination(isPresented: $navigateToPreview) {
                PhotoPreviewView(viewModel: viewModel)
            }
        }
    }
}

// MARK: - PhotoPicker wrapper (uses PHPickerViewController) -----------------

struct PHPickerSwiftUI: UIViewControllerRepresentable {
    @Binding var selectedImage: UIImage?
    var onDismiss: (UIImage?) -> Void

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = .photoLibrary
        picker.delegate = context.coordinator
        return picker
    }

    func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    class Coordinator: NSObject, UINavigationControllerDelegate, UIImagePickerControllerDelegate {
        let parent: PHPickerSwiftUI

        init(_ parent: PHPickerSwiftUI) {
            self.parent = parent
        }

        func imagePickerController(_ picker: UIImagePickerController, didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]) {
            let image = info[.originalImage] as? UIImage
            parent.selectedImage = image
            picker.dismiss(animated: true) {
                self.parent.onDismiss(image)
            }
        }

        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            picker.dismiss(animated: true)
        }
    }
}

// MARK: - Photo Preview ----------------------------------------------------

/// Screen 3 — User confirms photo before analysis.
///
/// Psychology: Build anticipation, give user control.
struct PhotoPreviewView: View {
    @ObservedObject var viewModel: PhotoViewModel
    @EnvironmentObject var appState: AppState
    @State private var navigateToProcessing = false

    var body: some View {
        ZStack {
            LXColor.black.ignoresSafeArea()

            VStack(spacing: 32) {
                Text("Is this the\nright photo?")
                    .lxH2()
                    .foregroundColor(LXColor.white)
                    .multilineTextAlignment(.center)

                if let img = viewModel.selectedImage {
                    Image(uiImage: img)
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .frame(height: 300)
                        .cornerRadius(LXConstants.cornerRadius)
                        .padding(.horizontal, LXConstants.standardPadding)
                }

                HStack(spacing: 20) {
                    Button(action: { /* dismiss back to camera */ }) {
                        HStack(spacing: 6) {
                            Image(systemName: "arrow.counterclockwise")
                            Text("Retake")
                        }
                        .lxBody()
                        .frame(maxWidth: .infinity)
                        .frame(height: LXConstants.buttonHeight)
                        .background(LXColor.deepNavy)
                        .foregroundColor(LXColor.white)
                        .cornerRadius(LXConstants.cornerRadius)
                    }

                    Button(action: {
                        viewModel.upload(appState: appState)
                        navigateToProcessing = true
                    }) {
                        HStack(spacing: 6) {
                            Text("🚀")
                            Text("Analyze & Discover")
                        }
                        .font(LXFont.h3())
                        .frame(maxWidth: .infinity)
                        .frame(height: LXConstants.buttonHeight)
                        .background(LXColor.gold)
                        .foregroundColor(LXColor.black)
                        .cornerRadius(LXConstants.cornerRadius)
                    }
                }
                .padding(.horizontal, LXConstants.standardPadding)
            }
        }
        .navigationDestination(isPresented: $navigateToProcessing) {
            ProcessingView()
        }
    }
}

// MARK: - Preview ----------------------------------------------------------

#Preview {
    CameraView()
        .environmentObject(AppState())
}