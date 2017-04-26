#ifndef __FGRAB_BLOB_H__

#include <stdint.h>
#include <stdexcept>

struct BlobStructure
{
	uint16_t bbx0;
	uint16_t bbx1;
	uint16_t bby0;
	uint16_t bby1;
	uint16_t cogxl;
	uint16_t cogxh;
	uint16_t cogyl;
	uint16_t cogyh;
	uint16_t areal;
	uint16_t areah;
	uint16_t conto;
	uint16_t contd;
	uint16_t error;
	uint16_t _dummy0;
	uint16_t _dummy1;
	uint16_t _dummy2;
};

class Blob
{
private:
	unsigned char* m_blob_memory;

public:
	Blob(unsigned char* blob_memory)
		: m_blob_memory(blob_memory)
	{}

	uint16_t bbx0() const {
		return reinterpret_cast<BlobStructure*>(m_blob_memory)->bbx0;
	}

	uint16_t bby0() const {
		return reinterpret_cast<BlobStructure*>(m_blob_memory)->bby0;
	}

	uint16_t bbx1() const {
		return reinterpret_cast<BlobStructure*>(m_blob_memory)->bbx1;
	}

	uint16_t bby1() const {
		return reinterpret_cast<BlobStructure*>(m_blob_memory)->bby1;
	}

	uint32_t area() const {
		return (reinterpret_cast<BlobStructure*>(m_blob_memory)->areah << 16) + reinterpret_cast<BlobStructure*>(m_blob_memory)->areal;
	}

	uint16_t cogx() const {
		return (area() == 0) ? 0 : ((reinterpret_cast<BlobStructure*>(m_blob_memory)->cogxh << 16) + reinterpret_cast<BlobStructure*>(m_blob_memory)->cogxl) / area();
	}

	uint16_t cogy() const {
		return (area() == 0) ? 0 : ((reinterpret_cast<BlobStructure*>(m_blob_memory)->cogyh << 16) + reinterpret_cast<BlobStructure*>(m_blob_memory)->cogyl) / area();
	}

	uint16_t conto() const {
		return reinterpret_cast<BlobStructure*>(m_blob_memory)->conto;
	}

	uint16_t contd() const {
		return reinterpret_cast<BlobStructure*>(m_blob_memory)->contd;
	}

	uint16_t errorcode() const {
		return reinterpret_cast<BlobStructure*>(m_blob_memory)->error;
	}

	uint8_t blobs_per_column() const {
		return (errorcode() & 0x3);
	}

	bool blob_memory_overflow() const {
		return ((errorcode() & 0x4) != 0);
	}

	bool area_valid() const {
		return ((errorcode() & 0x10) != 0);
	}

	bool cogx_valid() const {
		return ((errorcode() & 0x20) != 0);
	}

	bool cogy_valid() const {
		return ((errorcode() & 0x40) != 0);
	}

	bool cont_valid() const {
		return ((errorcode() & 0x80) != 0);
	}
};

class BlobArray
{
private:
	unsigned char* m_blobs_memory;
	size_t m_blobs_memory_length;

public:

	static const unsigned int c_buffer_size;

	BlobArray(void* blobs_memory, size_t blobs_memory_length)
		: m_blobs_memory(reinterpret_cast<unsigned char*>(blobs_memory)), m_blobs_memory_length(blobs_memory_length)
	{}

	unsigned int count() const {
		return m_blobs_memory_length/sizeof(BlobStructure);
	}

	Blob operator[](unsigned int index) const {
		if (index >= count())
			throw std::runtime_error("array index out of bounds");
		return Blob(m_blobs_memory + index * sizeof(BlobStructure));
	}
};

const unsigned int BlobArray::c_buffer_size = (262144 * 32);

#endif
