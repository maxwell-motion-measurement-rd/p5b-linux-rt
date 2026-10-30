ENTRY(_start)
MEMORY { PRIVATE (rwx) : ORIGIN = 0x60000000, LENGTH = 2M }
PHDRS { image PT_LOAD FLAGS(7); }
SECTIONS {
  . = ORIGIN(PRIVATE);
  .text : { KEEP(*(.text.boot)) *(.text*) } > PRIVATE :image
  .rodata : { *(.rodata*) } > PRIVATE :image
  .data : { *(.data*) } > PRIVATE :image
  .bss (NOLOAD) : ALIGN(4096) {
    __bss_start = .; *(.bss*) *(COMMON); . = ALIGN(8); __bss_end = .;
  } > PRIVATE :image
  .stack (NOLOAD) : ALIGN(16) { . += 16K; __stack_top = .; } > PRIVATE :image
  ASSERT(__stack_top <= ORIGIN(PRIVATE) + LENGTH(PRIVATE), "private region overflow")
  /DISCARD/ : { *(.comment) *(.note*) }
}
