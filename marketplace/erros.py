"""Erros da aplicação: as telas mostram a mensagem sem precisar conhecer o banco."""


class ErroAplicacao(Exception):
    """Erro com mensagem pronta para mostrar ao usuário."""


class ErroValidacao(ErroAplicacao):
    """Dados inválidos ou operação que a regra de negócio não permite."""


class NaoAutorizado(ErroAplicacao):
    """O usuário não pode realizar esta operação."""


class ErroBanco(ErroAplicacao):
    """Falha informada pelo banco de dados."""


class TabelaAusente(ErroBanco):
    """O banco não tem as tabelas do marketplace."""


class ConexaoFalhou(ErroBanco):
    """Não foi possível conectar ao banco."""


class ErroArmazenamento(ErroAplicacao):
    """Falha ao enviar arquivos para o armazenamento."""
