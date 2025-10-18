# Owner: Dev 4
from __future__ import annotations
from typing import Iterable, List, Any, Dict
from ..core.filesystem_base import FilesystemBase

class LinkedFS(FilesystemBase):
    """
    Estrategia de **asignación enlazada**.

    Metadata esperada en self.file_table[name]:
      {
        "size_blocks": int,
        # Campos específicos de enlazada:
        # "chain": List[int]   # lista ordenada de índices físicos (longitud == size_blocks)
        # (Opcional) "overhead_blocks": 0
      }

    Convenciones del proyecto:
      - Tamaño lógico fijo (no crecer en write).
      - El bloque lógico k se encuentra en chain[k].
      - Leer a partir de 'offset' puede requerir "caminar" la cadena (coste simulado).
    """

    def create(self, name: str, size_blocks: int) -> None:
        """
        Crea un archivo y reserva 'size_blocks' bloques **no necesariamente contiguos**,
        construyendo una cadena enlazada (lista ordenada de índices físicos).

        Precondiciones:
          - name no existe.
          - size_blocks > 0.
          - Existe al menos 'size_blocks' bloques libres.

        Efectos (cuando se implemente):
          - Solicitar self.fsm.allocate(size_blocks, contiguous=False) -> lista de índices físicos.
          - Registrar chain ordenada y size_blocks en file_table[name].
        """
        self._assert_new_file(name)
        self._assert_positive_blocks(size_blocks)

        self._emit("create:start", strategy="linked", name=name, size_blocks=size_blocks)

        # TODO: reservar bloques dispersos, construir chain y registrar metadata.
        raise NotImplementedError("LinkedFS.create no implementado")

        # self._emit("create:done", strategy="linked", name=name, size_blocks=size_blocks)

    def delete(self, name: str) -> None:
        """
        Elimina el archivo 'name' liberando todos los bloques de su cadena.

        Precondiciones:
          - name existe.

        Efectos (cuando se implemente):
          - Recuperar chain de file_table[name] y liberar todos sus bloques.
          - Borrar metadata del catálogo.
        """
        self._assert_file_exists(name)

        self._emit("delete:start", strategy="linked", name=name)

        # TODO: liberar bloques de chain y eliminar metadata.
        raise NotImplementedError("LinkedFS.delete no implementado")

        # self._emit("delete:done", strategy="linked", name=name)

    def read(self, name: str, offset: int, n_blocks: int, access_mode: str = "seq") -> List[bytes]:
        """
        Lee 'n_blocks' desde 'offset' siguiendo la cadena enlazada.

        Precondiciones:
          - name existe.
          - offset >= 0, n_blocks > 0.
          - offset + n_blocks <= size_blocks.

        Efectos (cuando se implemente):
          - Resolver índices físicos via chain[offset:offset+n_blocks].
          - disk.read_block(i) por cada índice físico.
          - (Opcional) simular coste de traversal para llegar al offset.
        """
        self._assert_file_exists(name)
        self._assert_non_negative(offset)
        self._assert_positive_blocks(n_blocks)
        self._assert_range_within_size(name, offset, n_blocks)

        phys = self._resolve_range(name, offset, n_blocks)
        self._emit("read:start", strategy="linked", name=name, offset=offset, n_blocks=n_blocks, physical=phys)

        # TODO: leer del disco y devolver lista de bytes
        raise NotImplementedError("LinkedFS.read no implementado")

        # self._emit("read:done", strategy="linked", name=name, offset=offset, n_blocks=n_blocks, physical=phys)

    def write(self, name: str, offset: int, n_blocks: int, data: Iterable[bytes] | None = None) -> None:
        """
        Escribe 'n_blocks' desde 'offset' usando la cadena enlazada.

        Precondiciones:
          - name existe.
          - offset >= 0, n_blocks > 0.
          - offset + n_blocks <= size_blocks.
          - Si 'data' no es None, debe proveer 'n_blocks' elementos de tamaño <= block_size.
        """
        self._assert_file_exists(name)
        self._assert_non_negative(offset)
        self._assert_positive_blocks(n_blocks)
        self._assert_range_within_size(name, offset, n_blocks)

        phys = self._resolve_range(name, offset, n_blocks)
        self._emit("write:start", strategy="linked", name=name, offset=offset, n_blocks=n_blocks, physical=phys)

        # TODO: escribir en disk.write_block(...) por cada índice físico
        raise NotImplementedError("LinkedFS.write no implementado")

        # self._emit("write:done", strategy="linked", name=name, offset=offset, n_blocks=n_blocks, physical=phys)

    def _resolve_range(self, name: str, offset: int, n_blocks: int) -> List[int]:
        """
        Devuelve la lista de índices físicos para [offset, offset+n_blocks), usando chain.

        Precondiciones:
          - name existe.
          - offset >= 0, n_blocks > 0.
          - offset + n_blocks <= size_blocks.
        """
        self._assert_file_exists(name)
        self._assert_non_negative(offset)
        self._assert_positive_blocks(n_blocks)
        self._assert_range_within_size(name, offset, n_blocks)

        # TODO: devolver chain[offset:offset+n_blocks] a partir de metadata
        raise NotImplementedError("LinkedFS._resolve_range no implementado")
