// (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
// Inspector Module Header for DreamStudio ELF Inspection.
// Code is licensed under the GPLv3 License.

#ifndef INSPECTOR_H
#define INSPECTOR_H

#include <stdint.h>
#include <stddef.h>


#ifdef __cplusplus
extern "C" {
#endif


typedef struct BinaryFile BinaryFile;


typedef struct {
    uint8_t  elf_class;
    uint8_t  elf_data;
    uint16_t type;
    uint16_t machine;
    uint64_t entry;
    uint64_t program_header_offset;
    uint64_t section_header_offset;
    uint16_t program_header_count;
    uint16_t section_header_count;
    uint16_t section_name_string_table_index;
} ElfHeaderInfo;


typedef struct {
    uint32_t name_offset;
    uint32_t type;
    uint64_t address;
    uint64_t offset;
    uint64_t size;
    uint64_t flags;
} ElfSectionInfo;


BinaryFile *binary_file_open(const char *path);
void binary_file_close(BinaryFile *file);


int binary_file_read_elf_header(
    BinaryFile *file,
    ElfHeaderInfo *header);


size_t binary_file_get_section_count(
    const ElfHeaderInfo *header);


int binary_file_read_section(
    BinaryFile *file,
    const ElfHeaderInfo *header,
    uint16_t index,
    ElfSectionInfo *section);


char *binary_file_read_section_name(
    BinaryFile *file,
    const ElfHeaderInfo *header,
    const ElfSectionInfo *section);


const char *elf_class_name(uint8_t elf_class);
const char *elf_data_name(uint8_t elf_data);
const char *elf_machine_name(uint16_t machine);
const char *elf_type_name(uint16_t type);
const char *elf_section_type_name(uint32_t type);
const char *elf_section_flags_name(uint64_t flags);
void inspector_free(void *ptr);
const char *inspector_version(void);


#ifdef __cplusplus
}
#endif

#endif