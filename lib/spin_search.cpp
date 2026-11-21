// lib/followup.py の盤面探索 (重い部分) の C++ 版。ミノ操作と T スピン判定は lib/srs.py と同じ規則。
//
// 開始形状に 6 ミノ (I J L S Z O) を来た順にホールドなしで置き、最後の T で
// 指定した段 (0 始まり。連続していなくてもよい。例: 1,3 は 3 段目を残して 2・4 段目を消す TSD) を
// T スピン (Mini は除く) でちょうど消せる盤面をすべて求める。
// (使ったミノの集合, 盤面) を状態として、そこに到達できるミノ順の集合を手数ごとに求める。
//
// 使い方: spin_search <開始形状 (16 進)> <消す段 (0 始まり、カンマ区切り)> <max_height> [overhang]
// overhang はミノの文字の並び (例: "I"、"IJLSZO")。そのミノは 1 マス以上が max_height 段以内にあれば上にはみ出してよい
// ("-" や省略ならどのミノもはみ出せない)
// 出力: 1 行 = "<盤面 (16 進)> <ミノ順集合 (2 進 720 桁)>"。ミノ順集合のビットの意味は
//       lib/followup.py の ORDER_BIT と同じ (k 手目に未使用ミノの何番目を選んだかを WEIGHT で重み付け)。
// T の位置はここでは出さない (Python 側で lib/srs.py の find_tspin を使って求め直す)。

#include <algorithm>
#include <array>
#include <bitset>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

using u128 = unsigned __int128;
using Orders = std::bitset<720>;

constexpr int W = 10;
constexpr int H = 12;  // 盤面の高さ (積みは高々 8 段。その上に出現位置と回転の余白がある)
constexpr int MAX_HEIGHT_LIMIT = 8;
constexpr int XOFF = 2, YOFF = 2;
constexpr int NX = W + XOFF, NY = H + YOFF;
constexpr int NSTATE = 4 * NX * NY;
constexpr int WEIGHT[6] = {1, 6, 30, 120, 360, 720};
constexpr const char* NAMES = "IJLSZO";

u128 bit(int x, int y) { return (u128)1 << (y * W + x); }
u128 row_mask(int y) { return (((u128)1 << W) - 1) << (y * W); }
int bit_length(u128 b) {
    uint64_t hi = (uint64_t)(b >> 64), lo = (uint64_t)b;
    return hi ? 128 - __builtin_clzll(hi) : lo ? 64 - __builtin_clzll(lo) : 0;
}
int popcount(u128 b) { return __builtin_popcountll((uint64_t)b) + __builtin_popcountll((uint64_t)(b >> 64)); }

const int KICKS_JLSTZ[8][5][2] = {
    // (0,1) (1,0) (1,2) (2,1) (2,3) (3,2) (3,0) (0,3) の順
    {{0, 0}, {-1, 0}, {-1, 1}, {0, -2}, {-1, -2}}, {{0, 0}, {1, 0}, {1, -1}, {0, 2}, {1, 2}},
    {{0, 0}, {1, 0}, {1, -1}, {0, 2}, {1, 2}},     {{0, 0}, {-1, 0}, {-1, 1}, {0, -2}, {-1, -2}},
    {{0, 0}, {1, 0}, {1, 1}, {0, -2}, {1, -2}},    {{0, 0}, {-1, 0}, {-1, -1}, {0, 2}, {-1, 2}},
    {{0, 0}, {-1, 0}, {-1, -1}, {0, 2}, {-1, 2}},  {{0, 0}, {1, 0}, {1, 1}, {0, -2}, {1, -2}},
};
const int KICKS_I[8][5][2] = {
    {{0, 0}, {-2, 0}, {1, 0}, {-2, -1}, {1, 2}}, {{0, 0}, {2, 0}, {-1, 0}, {2, 1}, {-1, -2}},
    {{0, 0}, {-1, 0}, {2, 0}, {-1, 2}, {2, -1}}, {{0, 0}, {1, 0}, {-2, 0}, {1, -2}, {-2, 1}},
    {{0, 0}, {2, 0}, {-1, 0}, {2, 1}, {-1, -2}}, {{0, 0}, {-2, 0}, {1, 0}, {-2, -1}, {1, 2}},
    {{0, 0}, {1, 0}, {-2, 0}, {1, -2}, {-2, 1}}, {{0, 0}, {-1, 0}, {2, 0}, {-1, 2}, {2, -1}},
};

int kick_table(int from, int to) {
    const int pairs[8][2] = {{0, 1}, {1, 0}, {1, 2}, {2, 1}, {2, 3}, {3, 2}, {3, 0}, {0, 3}};
    for (int i = 0; i < 8; i++)
        if (pairs[i][0] == from && pairs[i][1] == to) return i;
    std::abort();
}

struct Piece {
    int nrot = 4;
    std::array<u128, NSTATE> mask{};
    std::array<bool, NSTATE> valid{};
    std::array<int, NSTATE> down{};
    std::array<std::vector<int>, NSTATE> moves;
    // rots[s][d] = 回転 (d=0 が右回転、d=1 が左回転) の候補 (移動先, キック番号)。盤外の候補は除く
    std::array<std::array<std::vector<std::pair<int, int>>, 2>, NSTATE> rots;
    std::vector<std::vector<int>> by_y = std::vector<std::vector<int>>(NY);

    static int index(int r, int x, int y) { return (r * NX + x + XOFF) * NY + y + YOFF; }
    int index_or_none(int r, int x, int y) const {
        if (x < -XOFF || x >= W || y < -YOFF || y >= H) return -1;
        int s = index(r, x, y);
        return valid[s] ? s : -1;
    }
    static void decode(int s, int& r, int& x, int& y) {
        r = s / (NX * NY);
        int rest = s % (NX * NY);
        x = rest / NY - XOFF;
        y = rest % NY - YOFF;
    }

    Piece(char name) {
        int size;
        std::vector<std::pair<int, int>> cells;
        switch (name) {
            case 'I': size = 4; cells = {{0, 2}, {1, 2}, {2, 2}, {3, 2}}; break;
            case 'O': size = 2; cells = {{0, 0}, {1, 0}, {0, 1}, {1, 1}}; break;
            case 'T': size = 3; cells = {{1, 2}, {0, 1}, {1, 1}, {2, 1}}; break;
            case 'S': size = 3; cells = {{1, 2}, {2, 2}, {0, 1}, {1, 1}}; break;
            case 'Z': size = 3; cells = {{0, 2}, {1, 2}, {1, 1}, {2, 1}}; break;
            case 'J': size = 3; cells = {{0, 2}, {0, 1}, {1, 1}, {2, 1}}; break;
            case 'L': size = 3; cells = {{2, 2}, {0, 1}, {1, 1}, {2, 1}}; break;
            default: std::abort();
        }
        nrot = name == 'O' ? 1 : 4;
        std::vector<std::vector<std::pair<int, int>>> shapes = {cells};
        for (int i = 1; i < nrot; i++) {
            std::vector<std::pair<int, int>> next;
            for (auto [x, y] : shapes.back()) next.push_back({y, size - 1 - x});  // 時計回り
            shapes.push_back(next);
        }
        for (int r = 0; r < nrot; r++)
            for (int x = -XOFF; x < W; x++)
                for (int y = -YOFF; y < H; y++) {
                    u128 m = 0;
                    bool ok = true;
                    for (auto [cx, cy] : shapes[r]) {
                        int px = x + cx, py = y + cy;
                        if (px < 0 || px >= W || py < 0 || py >= H) { ok = false; break; }
                        m |= bit(px, py);
                    }
                    int s = index(r, x, y);
                    valid[s] = ok;
                    mask[s] = m;
                    down[s] = -1;
                }
        const auto& kicks = name == 'I' ? KICKS_I : KICKS_JLSTZ;
        for (int r = 0; r < nrot; r++)
            for (int x = -XOFF; x < W; x++)
                for (int y = -YOFF; y < H; y++) {
                    int s = index(r, x, y);
                    if (!valid[s]) continue;
                    by_y[y + YOFF].push_back(s);
                    const int d[3][2] = {{-1, 0}, {1, 0}, {0, -1}};
                    for (auto [dx, dy] : d) {
                        int t = index_or_none(r, x + dx, y + dy);
                        if (t < 0) continue;
                        moves[s].push_back(t);
                        if (dy) down[s] = t;
                    }
                    if (nrot == 1) continue;
                    for (int k = 0; k < 2; k++) {
                        int r2 = (r + (k == 0 ? 1 : 3)) % 4;
                        int tbl = kick_table(r, r2);
                        for (int i = 0; i < 5; i++) {
                            int t = index_or_none(r2, x + kicks[tbl][i][0], y + kicks[tbl][i][1]);
                            if (t >= 0) rots[s][k].push_back({t, i});
                        }
                    }
                }
    }

    // 操作 (左右移動・落下・左右回転) で到達できる全状態。積みの高さの段から探索を始める
    std::vector<int> reachable(u128 board, std::vector<char>& seen) const {
        int height = (bit_length(board) + W - 1) / W;
        std::fill(seen.begin(), seen.end(), 0);
        std::vector<int> stack = by_y[height + YOFF], out;
        for (int s : stack) seen[s] = 1;
        while (!stack.empty()) {
            int s = stack.back();
            stack.pop_back();
            out.push_back(s);
            for (int t : moves[s])
                if (!seen[t] && !(mask[t] & board)) { seen[t] = 1; stack.push_back(t); }
            for (int k = 0; k < 2; k++)
                for (auto [t, kick] : rots[s][k])
                    if (!(mask[t] & board)) {  // 最初に入るキックだけが採用される
                        if (!seen[t]) { seen[t] = 1; stack.push_back(t); }
                        break;
                    }
        }
        return out;
    }

    std::vector<u128> placements(u128 board, std::vector<char>& seen) const {
        std::vector<u128> out;
        for (int s : reachable(board, seen)) {
            int d = down[s];
            if (d < 0 || (mask[d] & board)) out.push_back(mask[s]);
        }
        std::sort(out.begin(), out.end());
        out.erase(std::unique(out.begin(), out.end()), out.end());
        return out;
    }
};

bool occupied(u128 board, int x, int y) {
    if (!(0 <= x && x < W && y >= 0)) return true;
    return y < H && (board & bit(x, y));
}

// lib/srs.py の find_tspin と同じ判定 (見つかったかどうかだけを返す)
bool find_tspin(const Piece& t, u128 board, u128 target, int need, std::vector<char>& seen) {
    if (popcount(board & target) < need) return false;
    const int corners[4][2] = {{-1, -1}, {1, -1}, {-1, 1}, {1, 1}};
    const int front[4][2][2] = {{{-1, 1}, {1, 1}}, {{1, 1}, {1, -1}}, {{-1, -1}, {1, -1}}, {{-1, -1}, {-1, 1}}};
    for (int s : t.reachable(board, seen)) {
        for (int k = 0; k < 2; k++) {
            for (auto [dst, kick] : t.rots[s][k]) {
                if (t.mask[dst] & board) continue;
                int d = t.down[dst];
                u128 nb = board | t.mask[dst];
                if ((d < 0 || (t.mask[d] & board)) && (nb & target) == target) {
                    bool extra = false;
                    for (int y = 0; y < H; y++) {
                        u128 r = row_mask(y);
                        if ((t.mask[dst] & r) && !(target & r) && (nb & r) == r) extra = true;
                    }
                    if (!extra) {
                        int r, x, y;
                        Piece::decode(dst, r, x, y);
                        int cx = x + 1, cy = y + 1, n = 0;
                        for (auto& c : corners) n += occupied(board, cx + c[0], cy + c[1]);
                        bool f = occupied(board, cx + front[r][0][0], cy + front[r][0][1]) &&
                                 occupied(board, cx + front[r][1][0], cy + front[r][1][1]);
                        if (n >= 3 && (f || kick == 4)) return true;
                    }
                }
                break;
            }
        }
    }
    return false;
}

struct BoardHash {
    size_t operator()(u128 b) const {
        uint64_t lo = (uint64_t)b, hi = (uint64_t)(b >> 64);
        return std::hash<uint64_t>{}(lo ^ (hi * 0x9e3779b97f4a7c15ULL));
    }
};

u128 parse_hex(const char* s) {
    u128 v = 0;
    for (; *s; s++) v = v * 16 + (*s <= '9' ? *s - '0' : (*s | 32) - 'a' + 10);
    return v;
}

std::string to_hex(u128 v) {
    if (!v) return "0";
    std::string s;
    for (; v; v >>= 4) s += "0123456789abcdef"[(int)(v & 15)];
    return {s.rbegin(), s.rend()};
}

int main(int argc, char** argv) {
    if (argc != 4 && argc != 5) {
        std::fprintf(stderr, "usage: %s <start-hex> <rows> <max_height> [overhang]\n", argv[0]);
        return 2;
    }
    u128 start = parse_hex(argv[1]);
    std::vector<int> rows;
    for (const char* q = argv[2]; *q;) {
        rows.push_back(std::atoi(q));
        while (*q && *q != ',') q++;
        if (*q == ',') q++;
    }
    std::sort(rows.begin(), rows.end());
    int max_height = std::atoi(argv[3]);
    std::string overhang = argc == 5 ? argv[4] : "";
    if (max_height > MAX_HEIGHT_LIMIT) {
        std::fprintf(stderr, "max_height は %d 以下\n", MAX_HEIGHT_LIMIT);
        return 2;
    }
    // はみ出しを許すと積みが最大 max_height + 3 段になり、その上に出現と回転の余白 (3 段) が要る
    if (overhang.find_first_not_of('-') != std::string::npos && max_height + 6 > H) {
        std::fprintf(stderr, "はみ出しを許すときの max_height は %d 以下\n", H - 6);
        return 2;
    }
    // T を置く前に消す段の中で埋まっている必要があるマス数 = 段数 x 10 - (T が消す段に入れる最大のマス数)。
    // 連続した 1 / 2 / 3 段は 3 / 4 / 4 (TSS / TSD / TST)、1 段あけた 2 段 (縦向きの T) は 2
    int lines = (int)rows.size(), need;
    bool contiguous = rows.back() - rows.front() == lines - 1;
    if (contiguous && lines <= 3) need = lines * W - (lines == 1 ? 3 : 4);
    else if (lines == 2 && rows[1] - rows[0] == 2) need = 2 * W - 2;
    else {
        std::fprintf(stderr, "T スピンでは消せない段の組み合わせです\n");
        return 2;
    }
    u128 target = 0;
    for (int r : rows) target |= row_mask(r);
    int max_outside = popcount(start) + 24 - need;  // 消す段の外に置けるブロック数の上限
    u128 limit = ((u128)1 << (max_height * W)) - 1;

    std::vector<Piece> pieces;
    for (int i = 0; i < 6; i++) pieces.emplace_back(NAMES[i]);
    Piece tpiece('T');
    std::vector<char> seen(NSTATE);

    // layer[used] = 盤面 -> ミノ順集合
    std::vector<std::unordered_map<u128, Orders, BoardHash>> layer(64), next(64);
    Orders one;
    one.set(0);
    layer[0][start] = one;
    for (int k = 0; k < 6; k++) {
        for (auto& m : next) m.clear();
        for (int used = 0; used < 64; used++) {
            for (auto& [b, orders] : layer[used]) {
                u128 board = b;
                int rank = 0;
                for (int ci = 0; ci < 6; ci++) {
                    if (used >> ci & 1) continue;
                    Orders shifted = orders << (rank * WEIGHT[k]);
                    rank++;
                    auto& dst = next[used | 1 << ci];
                    for (u128 m : pieces[ci].placements(board, seen)) {
                        u128 nb = board | m;
                        // 高さの上限。overhang に含まれるミノは、一部が上限内にあればはみ出してよい
                        bool over = overhang.find(NAMES[ci]) != std::string::npos ? !(m & limit) : (m & ~limit) != 0;
                        if (over || popcount(nb & ~target) > max_outside) continue;
                        // 残りのミノを全部消す段に入れても、T の前に need マス埋まらないなら打ち切る
                        if (popcount(nb & target) + 4 * (5 - k) < need) continue;
                        // T より前にラインが消えてはいけない
                        bool full = false;
                        for (int y = 0; y < max_height; y++)
                            if ((nb & row_mask(y)) == row_mask(y)) { full = true; break; }
                        if (full) continue;
                        dst[nb] |= shifted;
                    }
                }
            }
        }
        std::swap(layer, next);
        size_t n = 0;
        for (auto& m : layer) n += m.size();
        std::fprintf(stderr, "  layer %d: %zu states\n", k + 1, n);
    }
    for (auto& [b, orders] : layer[63])
        if (find_tspin(tpiece, b, target, need, seen))
            std::printf("%s %s\n", to_hex(b).c_str(), orders.to_string().c_str());
    return 0;
}
