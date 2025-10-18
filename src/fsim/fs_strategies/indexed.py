# Owner: Dev 5
from __future__ import annotations
from typing import Iterable, List, Any, Dict
from ..core.filesystem_base import FilesystemBase

class IndexedFS(FilesystemBase):
    """
    Estrategia de **asignación indexada**.

    Metadata esperada en self.file_table[name]:
      {
        "size_blocks": int,
        # Campos específicos de indexada:
        # "index_block": int,       # bloque físico del índice
        # "data_blocks": List[int], # punteros a todos los bloques de datos
        # "overhead_blocks": 1      # (recomendado) para contabilizar el índice
      }

    Convenciones del proyecto:
      - Tamaño lógico fijo (no crecer en write).
      - Bloque lógico k → data_blocks[k].
      - Acceso requiere consultar primero el índice (coste que puede simularse).
    """

    def create(self, name: str, size_blocks: int) -> None:
        """
        Crea un archivo con un **bloque índice** que referencia 'size_blocks' bloques de datos.

        Precondiciones:
          - name no existe.
          - size_blocks > 0.
          - Existe espacio para 1 (índice) + size_blocks (datos).

        Efectos (cuando se implemente):
          - Reservar 1 bloque para el índice + 'size_blocks' bloques no contiguos (o contiguos si se desea).
          - Registrar en file_table[name] = {"size_blocks": size_blocks, "index_block": i, "data_blocks": [...], "overhead_blocks": 1}
          - (Opcional) escribir la tabla de punteros en el bloque índice (simulado).
        """
        self._assert_new_file(name)
        self._assert_positive_blocks(size_blocks)

        self._emit("create:start", strategy="indexed", name=name, size_blocks=size_blocks)

        # TODO: reservar bloque índice + data_blocks; registrar metadata.
        raise NotImplementedError("IndexedFS.create no implementado")

        # self._emit("create:done", strategy="indexed", name=name, size_blocks=size_blocks)

    def delete(self, name: str) -> None:
        """
        Elimina el archivo 'name' liberando el **bloque índice** y todos los **bloques de datos**.

        Precondiciones:
          - name existe.

        Efectos (cuando se implemente):
          - Recuperar index_block y data_blocks.
          - Liberar todos esos bloques en el fsm.
          - Borrar metadata del catálogo.
        """
        self._assert_file_exists(name)

        self._emit("delete:start", strategy="indexed", name=name)

        # TODO: liberar index_block + data_blocks; eliminar metadata.
        raise NotImplementedError("IndexedFS.delete no implementado")

        # self._emit("delete:done", strategy="indexed", name=name)

    def read(self, name: str, offset: int, n_blocks: int, access_mode: str = "seq") -> List[bytes]:
        """
        Lee 'n_blocks' desde 'offset' usando el bloque índice para resolver data_blocks.

        Precondiciones:
          - name existe.
          - offset >= 0, n_blocks > 0.
          - offset + n_blocks <= size_blocks.

        Efectos (cuando se implemente):
          - Consultar índice (simulado/implícito) y mapear a data_blocks[offset:offset+n_blocks].
          - disk.read_block(i) por cada bloque de datos.
        """
        self._assert_file_exists(name)
        self._assert_non_negative(offset)
        self._assert_positive_blocks(n_blocks)
        self._assert_range_within_size(name, offset, n_blocks)

        phys = self._resolve_range(name, offset, n_blocks)
        self._emit("read:start", strategy="indexed", name=name, offset=offset, n_blocks=n_blocks, physical=phys)

        # TODO: leer del disco y devolver lista de bytes
        raise NotImplementedError("IndexedFS.read no implementado")

        # self._emit("read:done", strategy="indexed", name=name, offset=offset, n_blocks=n_blocks, physical=phys)

    def write(self, name: str, offset: int, n_blocks: int, data: Iterable[bytes] | None = None) -> None:
        """
        Escribe 'n_blocks' desde 'offset' consultando el índice y accediendo data_blocks.

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
        self._emit("write:start", strategy="indexed", name=name, offset=offset, n_blocks=n_blocks, physical=phys)

        # TODO: escribir en disk.write_block(...) por cada bloque físico de datos
        raise NotImplementedError("IndexedFS.write no implementado")

        # self._emit("write:done", strategy="indexed", name=name, offset=offset, n_blocks=n_blocks, physical=phys)

    def _resolve_range(self, name: str, offset: int, n_blocks: int) -> List[int]:
        """
        Devuelve la lista de índices físicos para [offset, offset+n_blocks), usando data_blocks.

        Precondiciones:
          - name existe.
          - offset >= 0, n_blocks > 0.
          - offset + n_blocks <= size_blocks.
        """
        self._assert_file_exists(name)
        self._assert_non_negative(offset)
        self._assert_positive_blocks(n_blocks)
        self._assert_range_within_size(name, offset, n_blocks)

        # TODO: devolver sublista de data_blocks[offset:offset+n_blocks] a partir de metadata
        raise NotImplementedError("IndexedFS._resolve_range no implementado")
