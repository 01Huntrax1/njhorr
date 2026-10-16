// Njohrr: file access for the preset / sample / wavetable managers.
// Everything lives in <Documents>/Njohrr/{Presets,Samples,Wavetables}.
// Only plain file names inside those folders are accepted (no paths).
#pragma once

#include <string>
#include <vector>
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <cstdlib>
#include <cstdint>
#include <chrono>

#if defined (_WIN32)
 #ifndef WIN32_LEAN_AND_MEAN
  #define WIN32_LEAN_AND_MEAN
 #endif
 #ifndef NOMINMAX
  #define NOMINMAX
 #endif
 #include <windows.h>
 #include <shlobj.h>
 #include <shellapi.h>
#endif

namespace njohrr
{

namespace fs = std::filesystem;

//==============================================================================
inline std::string b64encode (const std::string& in)
{
    static const char* t = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string out;
    out.reserve ((in.size() + 2) / 3 * 4);
    size_t i = 0;

    for (; i + 2 < in.size(); i += 3)
    {
        auto n = (uint32_t (uint8_t (in[i])) << 16) | (uint32_t (uint8_t (in[i + 1])) << 8) | uint32_t (uint8_t (in[i + 2]));
        out += t[(n >> 18) & 63]; out += t[(n >> 12) & 63]; out += t[(n >> 6) & 63]; out += t[n & 63];
    }

    if (i + 1 == in.size())
    {
        auto n = uint32_t (uint8_t (in[i])) << 16;
        out += t[(n >> 18) & 63]; out += t[(n >> 12) & 63]; out += "==";
    }
    else if (i + 2 == in.size())
    {
        auto n = (uint32_t (uint8_t (in[i])) << 16) | (uint32_t (uint8_t (in[i + 1])) << 8);
        out += t[(n >> 18) & 63]; out += t[(n >> 12) & 63]; out += t[(n >> 6) & 63]; out += '=';
    }

    return out;
}

inline bool b64decode (const std::string& in, std::string& out)
{
    auto val = [] (char c) -> int
    {
        if (c >= 'A' && c <= 'Z') return c - 'A';
        if (c >= 'a' && c <= 'z') return c - 'a' + 26;
        if (c >= '0' && c <= '9') return c - '0' + 52;
        if (c == '+') return 62;
        if (c == '/') return 63;
        return -1;
    };

    out.clear();
    out.reserve (in.size() / 4 * 3);
    uint32_t acc = 0;
    int bits = 0;

    for (char c : in)
    {
        if (c == '=' || c == '\n' || c == '\r' || c == ' ') continue;
        auto v = val (c);
        if (v < 0) return false;
        acc = (acc << 6) | uint32_t (v);
        bits += 6;

        if (bits >= 8)
        {
            bits -= 8;
            out += char ((acc >> bits) & 0xff);
        }
    }

    return true;
}

//==============================================================================
inline fs::path getRootDir()
{
    fs::path docs;

   #if defined (_WIN32)
    wchar_t buf[MAX_PATH] = {};

    if (SHGetFolderPathW (nullptr, CSIDL_PERSONAL, nullptr, 0, buf) == S_OK)
        docs = fs::path (std::wstring (buf));
    else if (auto* p = std::getenv ("USERPROFILE"))
        docs = fs::path (p) / "Documents";
    else
        docs = fs::temp_directory_path();
   #else
    if (auto* h = std::getenv ("HOME"))
        docs = fs::path (h) / "Documents";
    else
        docs = fs::temp_directory_path();
   #endif

    return docs / "Njohrr";
}

inline const char* getKindFolder (const std::string& kind)
{
    if (kind == "presets")    return "Presets";
    if (kind == "samples")    return "Samples";
    if (kind == "wavetables") return "Wavetables";
    if (kind == "root")       return "";
    return nullptr;
}

inline bool isValidName (const std::string& n)
{
    if (n.empty() || n.size() > 200) return false;
    if (n[0] == '.' || n.back() == '.' || n.back() == ' ') return false;

    for (char c : n)
        if (static_cast<unsigned char> (c) < 32 || std::string ("/\\:*?\"<>|").find (c) != std::string::npos)
            return false;

    return true;
}

inline fs::path getFolder (const std::string& kind, std::error_code& ec)
{
    auto* k = getKindFolder (kind);

    if (k == nullptr)
    {
        ec = std::make_error_code (std::errc::invalid_argument);
        return {};
    }

    auto p = getRootDir() / k;
    fs::create_directories (p, ec);
    return p;
}

//==============================================================================
inline std::string jsonString (const std::string& s)
{
    std::string o = "\"";

    for (char c : s)
    {
        switch (c)
        {
            case '"':  o += "\\\""; break;
            case '\\': o += "\\\\"; break;
            case '\n': o += "\\n";  break;
            case '\r': o += "\\r";  break;
            case '\t': o += "\\t";  break;
            default:
                if (static_cast<unsigned char> (c) < 32) { char b[8]; std::snprintf (b, sizeof (b), "\\u%04x", (unsigned) c); o += b; }
                else o += c;
        }
    }

    return o + "\"";
}

inline std::string fail (const std::string& why)  { return "{\"ok\":false,\"error\":" + jsonString (why) + "}"; }
inline std::string pathToUtf8 (const fs::path& p)
{
   #if defined (__cpp_lib_char8_t)
    auto u = p.u8string();
    return std::string (u.begin(), u.end());
   #else
    return p.u8string();
   #endif
}

inline fs::path fromUtf8 (const std::string& s)
{
   #if defined (__cpp_lib_char8_t)
    return fs::path (std::u8string (s.begin(), s.end()));
   #else
    return fs::u8path (s);
   #endif
}

inline void revealFolder (const fs::path& folder)
{
   #if defined (_WIN32)
    ShellExecuteW (nullptr, L"open", folder.wstring().c_str(), nullptr, nullptr, SW_SHOWNORMAL);
   #else
    std::string p = pathToUtf8 (folder), q = "'";

    for (char c : p)
    {
        if (c == '\'') q += "'\\''";
        else q += c;
    }

    q += "'";
   #if defined (__APPLE__)
    auto cmd = "open " + q + " >/dev/null 2>&1 &";
   #else
    auto cmd = "xdg-open " + q + " >/dev/null 2>&1 &";
   #endif
    auto r = std::system (cmd.c_str());
    (void) r;
   #endif
}

//==============================================================================
/// op: info | list | read | write | delete | move | reveal. Always returns a JSON string.
inline std::string handle (const std::string& op, const std::string& kind, const std::string& name, const std::string& arg)
{
    try
    {
        std::error_code ec;

        if (op == "info")
        {
            for (auto* k : { "presets", "samples", "wavetables" })
                getFolder (k, ec);

            if (ec) return fail ("cannot create folders: " + ec.message());
            return "{\"ok\":true,\"root\":" + jsonString (pathToUtf8 (getRootDir())) + "}";
        }

        auto folder = getFolder (kind, ec);
        if (ec) return fail ("folder unavailable: " + ec.message());

        if (op == "list")
        {
            std::string out = "[";
            bool first = true;

            for (fs::directory_iterator it (folder, ec), end; ! ec && it != end; it.increment (ec))
            {
                std::error_code e2;
                if (! it->is_regular_file (e2)) continue;
                auto fn = pathToUtf8 (it->path().filename());
                if (fn.empty() || fn[0] == '.' || (fn.size() > 4 && fn.compare (fn.size() - 4, 4, ".tmp") == 0)) continue;
                auto size = (long long) it->file_size (e2);
                // file_clock -> unix seconds without relying on C++20 clock_cast
                auto ft = it->last_write_time (e2);
                auto sysNow = std::chrono::system_clock::now();
                auto fileNow = fs::file_time_type::clock::now();
                auto mt = (long long) std::chrono::duration_cast<std::chrono::seconds> ((sysNow + (ft - fileNow)).time_since_epoch()).count();
                out += std::string (first ? "" : ",") + "{\"name\":" + jsonString (fn) + ",\"size\":" + std::to_string (size) + ",\"mtime\":" + std::to_string (mt) + "}";
                first = false;
            }

            return out + "]";
        }

        if (op == "reveal")
        {
            revealFolder (folder);
            return "{\"ok\":true}";
        }

        if (! isValidName (name)) return fail ("invalid file name");
        auto file = folder / fromUtf8 (name);

        if (op == "read")
        {
            std::ifstream in (file, std::ios::binary);
            if (! in) return fail ("cannot open file");
            std::string data ((std::istreambuf_iterator<char> (in)), std::istreambuf_iterator<char>());
            if (data.size() > 96u * 1024u * 1024u) return fail ("file too large");
            return "{\"ok\":true,\"data\":\"" + b64encode (data) + "\"}";
        }

        if (op == "write")
        {
            std::string data;
            if (! b64decode (arg, data)) return fail ("bad data");
            if (data.size() > 96u * 1024u * 1024u) return fail ("file too large");
            auto tmp = file;
            tmp += ".tmp";

            {
                std::ofstream out (tmp, std::ios::binary | std::ios::trunc);
                if (! out) return fail ("cannot write file");
                out.write (data.data(), (std::streamsize) data.size());
                out.flush();
                if (! out) { out.close(); fs::remove (tmp, ec); return fail ("write failed (disk full?)"); }
            }

            fs::rename (tmp, file, ec);

            if (ec)
            {
                std::error_code e2;
                fs::remove (file, e2);
                fs::rename (tmp, file, ec);
            }

            if (ec) { std::error_code e3; fs::remove (tmp, e3); return fail ("cannot save file: " + ec.message()); }
            return "{\"ok\":true}";
        }

        if (op == "delete")
        {
            if (! fs::exists (file, ec)) return fail ("file not found");
            fs::remove (file, ec);
            if (ec) return fail ("cannot delete: " + ec.message());
            return "{\"ok\":true}";
        }

        if (op == "move")
        {
            auto slash = arg.find ('/');
            if (slash == std::string::npos) return fail ("bad target");
            auto newKind = arg.substr (0, slash), newName = arg.substr (slash + 1);
            if (! isValidName (newName)) return fail ("invalid new name");
            auto newFolder = getFolder (newKind, ec);
            if (ec) return fail ("target folder unavailable");
            auto target = newFolder / fromUtf8 (newName);
            if (! fs::exists (file, ec)) return fail ("file not found");
            if (fs::exists (target, ec) && ! (fs::equivalent (file, target, ec) && ! ec)) return fail ("a file with that name already exists");
            fs::rename (file, target, ec);
            if (ec) return fail ("cannot move: " + ec.message());
            return "{\"ok\":true}";
        }

        return fail ("unknown operation");
    }
    catch (const std::exception& e)
    {
        return fail (std::string ("error: ") + e.what());
    }
}

} // namespace njohrr
