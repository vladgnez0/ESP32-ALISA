#include <cstdint>
#include <cstring>
#include <vector>
#include <string>

using namespace std;

const uint8_t Pi[8][16] = {
    {12, 4, 6, 2, 10, 5, 11, 9, 14, 8, 13, 7, 0, 3, 15, 1},
    {6, 8, 2, 3, 9, 10, 5, 12, 1, 14, 4, 7, 11, 13, 0, 15},
    {11, 3, 5, 8, 2, 15, 10, 13, 14, 1, 7, 4, 12, 9, 6, 0},
    {12, 8, 2, 1, 13, 4, 15, 6, 7, 0, 10, 5, 3, 14, 9, 11},
    {7, 15, 5, 10, 8, 1, 6, 13, 0, 9, 3, 14, 11, 4, 2, 12},
    {5, 13, 15, 6, 9, 2, 12, 10, 11, 7, 8, 1, 4, 3, 14, 0},
    {8, 14, 2, 5, 6, 9, 1, 12, 15, 4, 11, 0, 13, 10, 3, 7},
    {1, 7, 14, 13, 0, 5, 8, 3, 4, 15, 10, 6, 9, 12, 11, 2}
};

typedef uint8_t vect4[4];
vect4 iter_keys[32];

// Преобразование T
void magma_T(const uint8_t* in, uint8_t* out) {
    for (int i = 0; i < 4; i++) {
        uint8_t a = (in[i] & 0xF0) >> 4;
        uint8_t b = in[i] & 0x0F;
        a = Pi[i * 2 + 1][a];
        b = Pi[i * 2][b];
        out[i] = (a << 4) | b;
    }
}

// Побитовое XOR
void magma_add(const uint8_t* a, const uint8_t* b, uint8_t* c) {
    for (int i = 0; i < 4; i++)
        c[i] = a[i] ^ b[i];
}

// Сложение по модулю 2^32
void magma_add32(const uint8_t* a, const uint8_t* b, uint8_t* c) {
    uint16_t carry = 0;
    for (int i = 0; i < 4; i++) {
        carry += a[i] + b[i];
        c[i] = carry & 0xFF;
        carry >>= 8;
    }
}

// Функция g
void magma_g(const uint8_t* k, const uint8_t* a, uint8_t* out) {
    uint8_t tmp[4];
    magma_add32(a, k, tmp);
    magma_T(tmp, tmp);

    uint32_t val = (tmp[3] << 24) | (tmp[2] << 16) | (tmp[1] << 8) | tmp[0];
    val = (val << 11) | (val >> 21);

    out[0] = val & 0xFF;
    out[1] = (val >> 8) & 0xFF;
    out[2] = (val >> 16) & 0xFF;
    out[3] = (val >> 24) & 0xFF;
}

// Функция G
void magma_G(const uint8_t* k, const uint8_t* a, uint8_t* out, bool final = false) {
    uint8_t a0[4], a1[4], G[4];
    memcpy(a0, a, 4);
    memcpy(a1, a + 4, 4);

    magma_g(k, a0, G);
    magma_add(a1, G, G);

    if (!final) {
        memcpy(out, G, 4);
        memcpy(out + 4, a0, 4);
    }
    else {
        memcpy(out, a0, 4);
        memcpy(out + 4, G, 4);
    }
}

// Генерация раундовых ключей
void expand_key(const uint8_t* key) {
    for (int i = 0; i < 8; i++)
        memcpy(iter_keys[i], key + (7 - i) * 4, 4);

    for (int i = 8; i < 16; i++)
        memcpy(iter_keys[i], iter_keys[i - 8], 4);

    for (int i = 16; i < 24; i++)
        memcpy(iter_keys[i], iter_keys[i - 16], 4);

    for (int i = 24; i < 32; i++)
        memcpy(iter_keys[i], key + (31 - i) * 4, 4);
}

// Шифрование блока
void magma_encrypt(const uint8_t* block, uint8_t* out) {
    uint8_t temp[8];
    memcpy(temp, block, 8);

    for (int round = 0; round < 31; round++) {
        magma_G(iter_keys[round], temp, temp);
    }
    magma_G(iter_keys[31], temp, out, true);
}

// Дешифрование блока
void magma_decrypt(const uint8_t* block, uint8_t* out) {
    uint8_t temp[8];
    memcpy(temp, block, 8);

    for (int round = 31; round > 0; round--) {
        magma_G(iter_keys[round], temp, temp);
    }
    magma_G(iter_keys[0], temp, out, true);
}

// Преобразование строки в байты с дополнением
vector<uint8_t> string_to_bytes(const string& str, size_t block_size = 8) {
    vector<uint8_t> bytes(str.begin(), str.end());
    if (bytes.size() > block_size) bytes.resize(block_size);
    else bytes.resize(block_size, 0);
    return bytes;
}

// Преобразование байтов в строку
string bytes_to_string(const uint8_t* bytes, size_t len) {
    string str(reinterpret_cast<const char*>(bytes), len);
    size_t end = str.find('\0');
    if (end != string::npos) str.resize(end);
    return str;
}