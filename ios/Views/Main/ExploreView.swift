import SwiftUI

/// Screen 8 — Explore / Marketplace (third tab).
///
/// Psychology: Aspiration + social proof.
/// See others' transformations and discover recommended products.
struct ExploreView: View {
    @EnvironmentObject var appState: AppState
    @State private var selectedSegment = 0

    var body: some View {
        NavigationStack {
            ZStack {
                LXColor.black.ignoresSafeArea()

                if case .loading = appState.exploreState, appState.exploreData == nil {
                    VStack(spacing: 16) {
                        ProgressView().tint(LXColor.gold)
                        Text("Loading...")
                            .lxBody()
                            .foregroundColor(LXColor.white)
                    }
                } else if case .error(let err) = appState.exploreState, appState.exploreData == nil {
                    VStack(spacing: 16) {
                        Text("Something went wrong")
                            .lxH3()
                            .foregroundColor(LXColor.white)
                        Text(err)
                            .lxCaption()
                            .foregroundColor(LXColor.white.opacity(0.5))
                        Button("Retry") {
                            Task { await appState.fetchExplore() }
                        }
                        .lxBody()
                        .foregroundColor(LXColor.gold)
                    }
                } else if let data = appState.exploreData {
                    ScrollView {
                        VStack(spacing: 24) {
                            Text("Explore")
                                .lxH1()
                                .foregroundColor(LXColor.white)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .padding(.horizontal, LXConstants.standardPadding)
                                .padding(.top, 16)

                            // Segmented picker
                            Picker("Category", selection: $selectedSegment) {
                                Text("Transformations").tag(0)
                                Text("Products").tag(1)
                                Text("Articles").tag(2)
                            }
                            .pickerStyle(.segmented)
                            .padding(.horizontal, LXConstants.standardPadding)

                            if selectedSegment == 0 {
                                transformationsSection(data)
                            } else if selectedSegment == 1 {
                                productsSection(data)
                            } else {
                                articlesSection(data)
                            }

                            Spacer().frame(height: 40)
                        }
                    }
                    .refreshable {
                        await appState.fetchExplore()
                    }
                } else {
                    VStack(spacing: 16) {
                        Text("No content")
                            .lxH3()
                            .foregroundColor(LXColor.white.opacity(0.5))
                        Button("Load") {
                            Task { await appState.fetchExplore() }
                        }
                        .lxBody()
                        .foregroundColor(LXColor.gold)
                    }
                }
            }
            .onAppear {
                if appState.exploreData == nil {
                    Task { await appState.fetchExplore() }
                }
            }
        }
    }

    // MARK: - Transformations ----------------------------------------------

    private func transformationsSection(_ data: ExploreData) -> some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
            ForEach(data.transformations) { tx in
                VStack(spacing: 8) {
                    HStack(spacing: 4) {
                        if let url = tx.beforeImageURL, let u = URL(string: url) {
                            AsyncImage(url: u) { img in
                                img.resizable().aspectRatio(contentMode: .fit)
                            } placeholder: {
                                Rectangle().fill(LXColor.deepNavy)
                            }
                            .frame(height: 100)
                            .cornerRadius(8)
                        }

                        if let url = tx.afterImageURL, let u = URL(string: url) {
                            AsyncImage(url: u) { img in
                                img.resizable().aspectRatio(contentMode: .fit)
                            } placeholder: {
                                Rectangle().fill(LXColor.deepNavy)
                            }
                            .frame(height: 100)
                            .cornerRadius(8)
                        }
                    }

                    Text("@\(tx.username)")
                        .lxCaption()
                        .foregroundColor(LXColor.white)
                    HStack(spacing: 8) {
                        Text(String(format: "%.0f", tx.beforeScore))
                            .strikethrough()
                            .lxCaption()
                            .foregroundColor(LXColor.white.opacity(0.5))
                        Image(systemName: "arrow.right")
                            .font(.system(size: 10))
                            .foregroundColor(LXColor.gold)
                        Text(String(format: "%.0f", tx.afterScore))
                            .lxCaption()
                            .foregroundColor(LXColor.gold)
                    }
                }
                .padding(8)
                .background(LXColor.deepNavy)
                .cornerRadius(LXConstants.cornerRadius)
            }
        }
        .padding(.horizontal, LXConstants.standardPadding)
    }

    // MARK: - Products -----------------------------------------------------

    private func productsSection(_ data: ExploreData) -> some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
            ForEach(data.products) { product in
                VStack(alignment: .leading, spacing: 8) {
                    if let url = product.imageURL, let u = URL(string: url) {
                        AsyncImage(url: u) { img in
                            img.resizable().aspectRatio(contentMode: .fill)
                        } placeholder: {
                            Rectangle().fill(LXColor.deepNavy)
                        }
                        .frame(height: 120)
                        .clipped()
                        .cornerRadius(8)
                    }

                    Text(product.name)
                        .lxBody()
                        .foregroundColor(LXColor.white)
                        .lineLimit(2)

                    Text(product.description)
                        .lxCaption()
                        .foregroundColor(LXColor.white.opacity(0.5))
                        .lineLimit(2)

                    HStack {
                        Text("$\(String(format: "%.2f", product.price))")
                            .lxBody()
                            .foregroundColor(LXColor.gold)

                        Spacer()

                        HStack(spacing: 2) {
                            Image(systemName: "star.fill")
                                .font(.system(size: 10))
                            Text(String(format: "%.1f", product.rating))
                        }
                        .lxCaption()
                        .foregroundColor(LXColor.gold)
                    }
                }
                .padding(8)
                .background(LXColor.deepNavy)
                .cornerRadius(LXConstants.cornerRadius)
            }
        }
        .padding(.horizontal, LXConstants.standardPadding)
    }

    // MARK: - Articles -----------------------------------------------------

    private func articlesSection(_ data: ExploreData) -> some View {
        LazyVStack(spacing: 12) {
            ForEach(data.articles) { article in
                Button(action: {
                    if let url = URL(string: article.url) {
                        UIApplication.shared.open(url)
                    }
                }) {
                    HStack(spacing: 12) {
                        if let url = article.imageURL, let u = URL(string: url) {
                            AsyncImage(url: u) { img in
                                img.resizable().aspectRatio(contentMode: .fill)
                            } placeholder: {
                                Rectangle().fill(LXColor.deepNavy)
                            }
                            .frame(width: 60, height: 60)
                            .cornerRadius(8)
                        }

                        VStack(alignment: .leading, spacing: 4) {
                            Text(article.title)
                                .lxBody()
                                .foregroundColor(LXColor.white)
                            Text(article.summary)
                                .lxCaption()
                                .foregroundColor(LXColor.white.opacity(0.5))
                                .lineLimit(2)
                        }

                        Spacer()

                        Image(systemName: "chevron.right")
                            .foregroundColor(LXColor.gold.opacity(0.5))
                    }
                    .padding()
                    .background(LXColor.deepNavy)
                    .cornerRadius(LXConstants.cornerRadius)
                }
            }
        }
        .padding(.horizontal, LXConstants.standardPadding)
    }
}

// MARK: - Preview ----------------------------------------------------------

#Preview {
    ExploreView()
        .environmentObject(AppState())
}