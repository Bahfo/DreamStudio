// (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
// Inspector Module Source Code for DreamStudio ELF Inspection.
// Code is licensed under the GPLv3 License.

#include "inspector.hpp"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>


struct BinaryFile {
    FILE *handle;
};


static uint16_t read_u16(
    const unsigned char *data,
    uint8_t elf_data) {

    if (elf_data == 1) {
        return (uint16_t)data[0] |
               ((uint16_t)data[1] << 8);
    }

    return ((uint16_t)data[0] << 8) |
           (uint16_t)data[1];
}


static uint32_t read_u32(
    const unsigned char *data,
    uint8_t elf_data) {

    if (elf_data == 1) {
        return (uint32_t)data[0] |
               ((uint32_t)data[1] << 8) |
               ((uint32_t)data[2] << 16) |
               ((uint32_t)data[3] << 24);
    }

    return ((uint32_t)data[0] << 24) |
           ((uint32_t)data[1] << 16) |
           ((uint32_t)data[2] << 8) |
           (uint32_t)data[3];
}


static uint64_t read_u64(
    const unsigned char *data,
    uint8_t elf_data) {

    if (elf_data == 1) {
        return (uint64_t)data[0] |
               ((uint64_t)data[1] << 8) |
               ((uint64_t)data[2] << 16) |
               ((uint64_t)data[3] << 24) |
               ((uint64_t)data[4] << 32) |
               ((uint64_t)data[5] << 40) |
               ((uint64_t)data[6] << 48) |
               ((uint64_t)data[7] << 56);
    }

    return ((uint64_t)data[0] << 56) |
           ((uint64_t)data[1] << 48) |
           ((uint64_t)data[2] << 40) |
           ((uint64_t)data[3] << 32) |
           ((uint64_t)data[4] << 24) |
           ((uint64_t)data[5] << 16) |
           ((uint64_t)data[6] << 8) |
           (uint64_t)data[7];
}


static size_t elf_header_size(uint8_t elf_class) {
    return (elf_class == 1) ? 52 : 64;
}


static size_t elf_section_header_size(uint8_t elf_class) {
    return (elf_class == 1) ? 40 : 64;
}


BinaryFile *binary_file_open(const char *path) {
    if (path == NULL) return NULL;

    FILE *handle = fopen(path, "rb");
    if (handle == NULL) return NULL;

    BinaryFile *file = static_cast<BinaryFile *>(malloc(sizeof(BinaryFile)));
    if (file == NULL) {
        fclose(handle);
        return NULL;
    }

    file->handle = handle;
    return file;
}


void binary_file_close(BinaryFile *file) {
    if (file == NULL) return;
    if (file->handle != NULL) fclose(file->handle);
    free(file);
}


int binary_file_read_elf_header(
    BinaryFile *file,
    ElfHeaderInfo *header) {

    if (file == NULL || file->handle == NULL || header == NULL)
        return 0;

    if (fseek(file->handle, 0, SEEK_SET) != 0)
        return 0;

    unsigned char ident[16];
    if (fread(ident, sizeof(ident), 1, file->handle) != 1)
        return 0;

    if (ident[0] != 0x7F || ident[1] != 'E' || ident[2] != 'L' || ident[3] != 'F')
        return 0;

    uint8_t elf_class = ident[4];
    uint8_t elf_data = ident[5];

    if (elf_data != 1 && elf_data != 2)
        return 0;

    if (elf_class != 1 && elf_class != 2)
        return 0;

    size_t hdr_size = elf_header_size(elf_class);
    unsigned char *header_data = static_cast<unsigned char *>(malloc(hdr_size));
    if (header_data == NULL)
        return 0;

    memcpy(header_data, ident, 16);

    if (fread(header_data + 16, hdr_size - 16, 1, file->handle) != 1) {
        free(header_data);
        return 0;
    }

    header->elf_class = elf_class;
    header->elf_data = elf_data;

    if (elf_class == 1) {
        header->type = read_u16(&header_data[16], elf_data);
        header->machine = read_u16(&header_data[18], elf_data);
        header->entry = read_u32(&header_data[24], elf_data);
        header->program_header_offset = read_u32(&header_data[28], elf_data);
        header->section_header_offset = read_u32(&header_data[32], elf_data);
        header->program_header_count = read_u16(&header_data[44], elf_data);
        header->section_header_count = read_u16(&header_data[46], elf_data);
        header->section_name_string_table_index = read_u16(&header_data[48], elf_data);
    } else {
        header->type = read_u16(&header_data[16], elf_data);
        header->machine = read_u16(&header_data[18], elf_data);
        header->entry = read_u64(&header_data[24], elf_data);
        header->program_header_offset = read_u64(&header_data[32], elf_data);
        header->section_header_offset = read_u64(&header_data[40], elf_data);
        header->program_header_count = read_u16(&header_data[56], elf_data);
        header->section_header_count = read_u16(&header_data[60], elf_data);
        header->section_name_string_table_index = read_u16(&header_data[62], elf_data);
    }

    free(header_data);
    return 1;
}


const char *elf_machine_name(uint16_t machine) {
    switch (machine) {
        case 0x03: return "x86";
        case 0x3E: return "x86-64";
        case 0x28: return "ARM";
        case 0xB7: return "AArch64";
        case 0xF3: return "RISC-V";
        default: return "Unknown";
    }
}


const char *elf_type_name(uint16_t type) {
    switch (type) {
        case 1: return "Relocatable";
        case 2: return "Executable";
        case 3: return "Shared Object";
        case 4: return "Core Dump";
        default: return "Unknown";
    }
}


const char *elf_class_name(uint8_t elf_class) {
    switch (elf_class) {
        case 1: return "ELF32";
        case 2: return "ELF64";
        default: return "Unknown";
    }
}


const char *elf_data_name(uint8_t elf_data) {
    switch (elf_data) {
        case 1: return "Little Endian";
        case 2: return "Big Endian";
        default: return "Unknown";
    }
}


size_t binary_file_get_section_count(
    const ElfHeaderInfo *header) {

    if (header == NULL) return 0;
    return header->section_header_count;
}


int binary_file_read_section(
    BinaryFile *file,
    const ElfHeaderInfo *header,
    uint16_t index,
    ElfSectionInfo *section) {

    if (file == NULL ||
        file->handle == NULL ||
        header == NULL ||
        section == NULL) return 0;

    if (index >= header->section_header_count) return 0;

    size_t section_header_size = elf_section_header_size(header->elf_class);

    uint64_t section_offset =
        header->section_header_offset +
        ((uint64_t)index * section_header_size);

    unsigned char *data = static_cast<unsigned char *>(malloc(section_header_size));
    if (data == NULL) return 0;

    if (fseek(
            file->handle,
            (long)section_offset,
            SEEK_SET
        ) != 0) {
        free(data);
        return 0;
    }

    if (fread(data, section_header_size, 1, file->handle) != 1) {
        free(data);
        return 0;
    }

    if (header->elf_class == 1) {
        section->name_offset = read_u32(&data[0], header->elf_data);
        section->type = read_u32(&data[4], header->elf_data);
        section->flags = read_u32(&data[8], header->elf_data);
        section->address = read_u32(&data[12], header->elf_data);
        section->offset = read_u32(&data[16], header->elf_data);
        section->size = read_u32(&data[20], header->elf_data);
    } else {
        section->name_offset = read_u32(&data[0], header->elf_data);
        section->type = read_u32(&data[4], header->elf_data);
        section->flags = read_u64(&data[8], header->elf_data);
        section->address = read_u64(&data[16], header->elf_data);
        section->offset = read_u64(&data[24], header->elf_data);
        section->size = read_u64(&data[32], header->elf_data);
    }

    free(data);
    return 1;
}


char *binary_file_read_section_name(
    BinaryFile *file,
    const ElfHeaderInfo *header,
    const ElfSectionInfo *section) {

    if (file == NULL ||
        file->handle == NULL ||
        header == NULL ||
        section == NULL) return NULL;

    ElfSectionInfo string_table;

    if (!binary_file_read_section(
            file,
            header,
            header->section_name_string_table_index,
            &string_table)) return NULL;

    if (section->name_offset >= string_table.size)
        return NULL;

    uint64_t name_offset =
        string_table.offset + section->name_offset;

    if (fseek(
            file->handle,
            (long)name_offset,
            SEEK_SET
        ) != 0) return NULL;

    size_t maximum_length =
        (size_t)(
            string_table.size -
            section->name_offset
        );

    if (maximum_length == 0)
        return NULL;

    char *buffer = static_cast<char *>(malloc(maximum_length + 1));
    if (buffer == NULL) return NULL;

    size_t bytes_read = fread(buffer, 1, maximum_length, file->handle);
    if (bytes_read == 0) {
        free(buffer);
        return NULL;
    }

    buffer[bytes_read] = '\0';

    size_t name_length = 0;
    while (name_length < bytes_read && buffer[name_length] != '\0')
        name_length++;

    char *name = static_cast<char *>(malloc(name_length + 1));
    if (name == NULL) {
        free(buffer);
        return NULL;
    }

    memcpy(name, buffer, name_length);
    name[name_length] = '\0';

    free(buffer);
    return name;
}


const char *elf_section_type_name(uint32_t type) {
    switch (type) {
        case 0:  return "NULL";
        case 1:  return "PROGBITS";
        case 2:  return "SYMTAB";
        case 3:  return "STRTAB";
        case 4:  return "RELA";
        case 5:  return "HASH";
        case 6:  return "DYNAMIC";
        case 7:  return "NOTE";
        case 8:  return "NOBITS";
        case 9:  return "REL";
        case 10: return "SHLIB";
        case 11: return "DYNSYM";
        case 14: return "INIT_ARRAY";
        case 15: return "FINI_ARRAY";
        case 16: return "PREINIT_ARRAY";
        case 17: return "GROUP";
        case 18: return "SYMTAB_SHNDX";
        default: return "UNKNOWN";
    }
}


const char *elf_section_flags_name(uint64_t flags) {
    if (flags == 0)
        return "-";

    static char result[4];

    size_t index = 0;

    if (flags & 0x1)
        result[index++] = 'W';

    if (flags & 0x2)
        result[index++] = 'A';

    if (flags & 0x4)
        result[index++] = 'X';

    result[index] = '\0';

    return result;
}


void inspector_free(void *ptr) {
    free(ptr);
}

const char *inspector_version(void) {
    return "0.1.0";
}
